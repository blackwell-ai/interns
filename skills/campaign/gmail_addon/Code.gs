/**
 * Blackwell Reply Assist. Gmail add-on.
 *
 * Open an email in Gmail, click the add-on, and it drafts a reply in your voice
 * from our past replies (the same backend the Slack /respond command uses). You
 * edit it in the sidebar and send. The reply goes out in-thread, as you.
 *
 * The add-on sends the open thread id and your edited text to our backend, with a
 * shared secret and your signed-in email. The backend checks the secret and that you
 * are a founder on every call, then does the drafting, sending, and corpus write-back.
 *
 * Setup (Project Settings -> Script properties):
 *   BACKEND_URL           the backend host (or set it in BACKEND_URL below)
 *   ADDON_SHARED_SECRET   must match the backend's ADDON_SHARED_SECRET env var
 * Also put the backend host in appsscript.json (urlFetchWhitelist).
 */

function backendBase_() {
  var prop = PropertiesService.getScriptProperties().getProperty('BACKEND_URL');
  var base = prop || 'https://slackwiz-production.up.railway.app';
  return base.replace(/\/+$/, '');
}

/** Sidebar shown when no message is open. */
function onHomepage(e) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('Reply Assist'))
    .addSection(CardService.newCardSection().addWidget(
      CardService.newTextParagraph().setText(
        'Open an email, then use this panel to draft a reply in your voice.')))
    .build();
}

/** Sidebar shown when a message is open: offer to draft a reply. */
function onGmailMessage(e) {
  var section = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph().setText(
      'Draft a reply grounded in how you have answered before.'))
    .addWidget(CardService.newTextButton()
      .setText('Draft a reply')
      .setOnClickAction(CardService.newAction().setFunctionName('onDraft')));
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('Reply Assist'))
    .addSection(section)
    .build();
}

/** The Gmail API thread id of the open message, read via the add-on's per-message
 *  access token (no broad mailbox scope needed). */
function threadIdFromEvent_(e) {
  GmailApp.setCurrentMessageAccessToken(e.gmail.accessToken);
  var msg = GmailApp.getMessageById(e.gmail.messageId);
  return msg.getThread().getId();
}

/** POST to the backend with the shared secret and the signed-in user's email.
 *  Throws on non-2xx. */
function callBackend_(path, payload) {
  var props = PropertiesService.getScriptProperties();
  var secret = props.getProperty('ADDON_SHARED_SECRET') || '';
  var email = Session.getEffectiveUser().getEmail();
  var res = UrlFetchApp.fetch(backendBase_() + path, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + secret,
      'X-Addon-User': email
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  var code = res.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error(code + ': ' + res.getContentText().slice(0, 200));
  }
  return JSON.parse(res.getContentText());
}

/** Draft (or re-draft) a reply and show it in an editable card. */
function onDraft(e) {
  var threadId;
  try {
    threadId = threadIdFromEvent_(e);
  } catch (err) {
    return notify_('Could not read this email.');
  }
  var data;
  try {
    data = callBackend_('/addon/draft', { thread_id: threadId });
  } catch (err) {
    return notify_('Draft failed. ' + err.message);
  }

  var meta = CardService.newTextParagraph().setText(
    'To: ' + (data.who || '(unknown)') + '  ·  ' +
    (data.n_examples || 0) + ' past examples  ·  ' + (data.category || 'other'));

  var input = CardService.newTextInput()
    .setFieldName('reply_body')
    .setTitle('Your reply (edit before sending)')
    .setMultiline(true)
    .setValue(data.draft || '');

  var send = CardService.newTextButton()
    .setText('Send reply')
    .setOnClickAction(CardService.newAction()
      .setFunctionName('onSend')
      .setParameters({ thread_id: threadId }));

  var regen = CardService.newTextButton()
    .setText('Regenerate')
    .setOnClickAction(CardService.newAction().setFunctionName('onDraft'));

  var section = CardService.newCardSection()
    .addWidget(meta)
    .addWidget(input)
    .addWidget(CardService.newButtonSet().addButton(send).addButton(regen));

  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('Review and send'))
    .addSection(section)
    .build();

  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation().updateCard(card))
    .build();
}

/** Send the edited reply. The backend derives who/what to reply to from the thread,
 *  sends in-thread as the founder, and records the sent reply as a gold example. */
function onSend(e) {
  var threadId = e.commonEventObject.parameters.thread_id;
  var body = '';
  try {
    body = e.commonEventObject.formInputs.reply_body.stringInputs.value[0];
  } catch (x) {
    body = '';
  }
  if (!body || !body.trim()) {
    return notify_('Nothing to send. The reply is empty.');
  }
  try {
    callBackend_('/addon/send', { thread_id: threadId, body: body });
  } catch (err) {
    return notify_('Send failed, nothing left your outbox. ' + err.message);
  }

  var done = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('Sent'))
    .addSection(CardService.newCardSection().addWidget(
      CardService.newTextParagraph().setText('Your reply is on its way.')))
    .build();

  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText('Sent.'))
    .setNavigation(CardService.newNavigation().updateCard(done))
    .setStateChanged(true)
    .build();
}

function notify_(text) {
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification().setText(text))
    .build();
}
