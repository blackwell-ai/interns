# Blackwell/Public Goods Kickoff

- Date: 2026-06-16
- Granola document id: db6e13c3-e066-4096-97d9-04f134f10b79
- Created at: 2026-06-16T18:29:34.716Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu), Scott Burack (scott@publicgoods.com), Armaan Priyadarshan (armaan.priyadarshan.29@dartmouth.edu), Shamit D'Souza (shamitd@stanford.edu), Michael Ferchak (michael@publicgoods.com)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 176 segments

---

## Notes

### Work Completed This Sprint

- Product data cards (fact cards) built for every PDP on the store
  - Covers variants, member price, shipping policy, Q&A, and reviews
  - Metadata added to enable cross-product and competitor comparisons
  - Improves AI and search engine visibility

- Brand identity card implemented as an invisible fact card on the homepage
  - Workaround to avoid front-end changes; creative team still exploring a visible version

- Shipping policy confusion resolved, including outdated 40% discount page
- LLMs.txt and [agents.md](http://agents.md) files ready, but need Shopify admin access to deploy (root-level files can’t be pushed via GitHub)

### Key Confirmations from Public Goods

- Legacy shipping policy: members who joined before April 2025 have a $45 minimum; everyone else has no minimum
- Okendo review meta fields (no underscores, all capitalized):
  - “Okendo Reviews Review Count”
  - “Okendo Reviews Average Rating”

- Scott to send the exact back-end meta field title over Slack

### Upcoming: New Product Launch

- Daily moisturizer with SPF launching in a day or two (Julie setting up the listing Wednesday or Thursday)
- New products will be handled automatically: script generates a fact card for each new SKU added to Shopify
- Goal: observe how the live metadata pipeline handles the new listing once pushed to production

### Phase 2 Workstreams

- Wikidata entry: can be done in a few hours; Samarjit to share draft with Scott before publishing
- Wikipedia article: more involved, lower priority for now
- Google info panel: no login needed; Samarjit to contact Scott if anything comes up
- Third-party review platforms (Trustpilot, BBB, Reddit): Public Goods to share logins
  - Replying to negative reviews is the primary approach
  - Posting new reviews is possible but platforms have bot detection; worth researching


### Next Steps

- Push PR to production after Scott creates a preview theme and confirms no front-end changes (Scott, today or tomorrow)
- Send LLMs.txt and [agents.md](http://agents.md) root-level files to Scott over Slack for manual Shopify upload (Samarjit)
- Verify the daily moisturizer with SPF fact card auto-generates correctly once live (Samarjit)
- Send meeting summary PDF to Michael and Scott (Samarjit)
- Share Wikidata draft with Scott for review before publishing (Samarjit)
- Obtain Trustpilot, BBB, and Reddit logins from Public Goods (Michael)

---

Chat with meeting transcript: [https://notes.granola.ai/t/06abd8b6-f927-4cd0-a36e-cdb3154cf6a0](https://notes.granola.ai/t/06abd8b6-f927-4cd0-a36e-cdb3154cf6a0)

---

Chat with meeting transcript: [https://notes.granola.ai/t/06abd8b6-f927-4cd0-a36e-cdb3154cf6a0](https://notes.granola.ai/t/06abd8b6-f927-4cd0-a36e-cdb3154cf6a0)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** Always disheveled.

**[00:22] Samarjit (mic):** We got. No, thanks, reply.

**[00:25] Samarjit (mic):** From Joanna. Heart song.

**[00:28] Samarjit (mic):** Who is Joan?

**[00:29] Samarjit (mic):** Na?

**[00:32] Samarjit (mic):** I got, like, a. I've been meeting with Peter chin today.

**[00:37] Samarjit (mic):** Like an actual meeting.

**[00:39] Samarjit (mic):** Okay, actually.

**[00:42] Samarjit (mic):** How did I, like, not end yet?

**[00:45] Samarjit (mic):** If I'm, like, still getting paid by them.

**[00:52] Samarjit (mic):** Things I'm, like, so confused, like, how you're making so much money.

**[01:00] Samarjit (mic):** You're, like, stealing all the money from the engagements?

**[01:03] Samarjit (mic):** No, I.

**[01:04] Samarjit (mic):** Haven't. It's all in.

**[01:04] Samarjit (mic):** Stripe.

**[01:06] Samarjit (mic):** Swing straight to your personal bank account.

**[01:08] Samarjit (mic):** It's not.

**[01:08] Samarjit (mic):** It's like.

**[01:09] Samarjit (mic):** All instead.

**[01:11] Samarjit (mic):** Of right. I took, like, the brax account.

**[02:12] Samarjit (mic):** Hi. How are you doing?

**[02:13] Other participant (system audio):** Good. How are you?

**[02:15] Samarjit (mic):** Doing good.

**[02:20] Samarjit (mic):** All right. Yeah, I think everyone has joined. So, yeah, we made a lot of progress over the last week.

**[02:26] Samarjit (mic):** I submitted a pull request earlier today, so you can review the progress. And I can also screen share the specific items we completed.

**[02:36] Other participant (system audio):** Sounds good? Yeah, I was looking it over before this meeting.

**[02:39] Other participant (system audio):** But yeah, if you want to review it.

**[02:42] Other participant (system audio):** That'd be good too.

**[02:44] Samarjit (mic):** So, yeah, I created this document sort of summarizing what we've built so far, and I can.

**[02:48] Other participant (system audio):** All right, just where did you send that? I don't know. I'm not seeing that.

**[02:53] Samarjit (mic):** Oh, this. This document I haven't sent it yet. I'll send it after the meeting.

**[02:59] Other participant (system audio):** He said he sent something before the meeting, a progress.

**[03:01] Samarjit (mic):** Oh, the pull request. Yeah, that was on GitHub.

**[03:03] Other participant (system audio):** Oh, on GitHub. That's why I didn't see it. Okay, cool.

**[03:06] Samarjit (mic):** Okay.

**[03:07] Samarjit (mic):** Yeah. So the. This summarizes what we built so far. So if you remember last time, the product, that card we built it for one PDP, now we've done it for every single PDP that the store has.

**[03:22] Samarjit (mic):** We've accounted for different variants.

**[03:25] Samarjit (mic):** We've included the member prize, the shipping policy, and the question and answer section. So this is all stuff that isn't visible to users, but is visible to lms and it sort of just gives information as to what each product is in a more detailed fashion. We've also added reviews information about reviews and the metadata for every single product, which allows it to compare products across Public Goods platform and between Public Goods and competitors to Public Goods. So this will, we hope that this will improve the visibility on AI and sear engines.

**[04:03] Samarjit (mic):** Another thing we discussed last time was a brand identity card. So if you remember, I suggested making a modification to the home page, and I think you mentioned that that would be sort of difficult to do. So we found a workaround where we can sort of just create invisible Fact card that tells the systems and informs sort of establishing the brand identity.

**[04:28] Samarjit (mic):** Without having to change what people see on the front end.

**[04:33] Samarjit (mic):** Okay, well, I mean, that, that, that's good.

**[04:36] Samarjit (mic):** I did ask our creative team, and they're going to check and see if they can do it anyway. I mean, you know, it'd be a good idea even.

**[04:46] Samarjit (mic):** To have that visible just for regular people to see, so. But let's Implement this, this invisible one that you're talking about, and then we'll still continue to pursue maybe a visible one. Yeah, this, this is already implemented. It's in the code base, but.

**[05:02] Samarjit (mic):** Yeah.

**[05:04] Samarjit (mic):** I.

**[05:05] Samarjit (mic):** Handle the confusion confusion surrounding the shipping policies and the dead 40 off page. There was a page saying that there was a 40 off discount, which I think was sort of outdated. So I fixed that.

**[05:20] Samarjit (mic):** Last time we built out the lm's txt. The agents are MD at the robots.txt. I realized this week that modifying this would require Shopify admin dashboard access.

**[05:32] Samarjit (mic):** It's. You can't do this through the, through the GitHub so I can either send those files over to you on slack or you can give me the Shopify.

**[05:46] Samarjit (mic):** To us.

**[05:48] Samarjit (mic):** Yeah.

**[05:53] Samarjit (mic):** Okay.

**[05:54] Samarjit (mic):** Yeah.

**[05:56] Samarjit (mic):** Yeah. Whichever is more convenient for you.

**[06:00] Samarjit (mic):** So, yeah, I think most files that live in sort of the root directory of the website. Yeah.

**[06:06] Samarjit (mic):** Okay.

**[06:08] Samarjit (mic):** Yeah. So big picture overview. I think all of this stuff in terms of metadata and handling the schema is basically complete. What's left for us to do is sort of work on a lot of the third party stuff.

**[06:24] Other participant (system audio):** On that.

**[06:28] Other participant (system audio):** As we launch new products, is this something that we need to update every time we launch a new product? We put a new skew on Shopify. Do we need to think about this specific issue? Or is there a file now that's going to be automatically generated? That will automatically get the important metadata. How's it going to work?

**[06:51] Samarjit (mic):** Yeah. So it'll, it'll, it'll happen automatically. So the way I did it was I created a script that automatically writes the fat card for every product. So if you launch a new product, this would, it would automatically have the information.

**[07:05] Other participant (system audio):** Okay.

**[07:06] Other participant (system audio):** As we do that next, there's a product that should be coming up in a day or two daily moisturizer with SPF. It's a new product that we're launching. Let's keep an eye on that and see what happens.

**[07:19] Samarjit (mic):** Okay, yeah, I'll make a note of that. I'll check to make sure that the.

**[07:24] Samarjit (mic):** Park info is automatically updated.

**[07:27] Other participant (system audio):** Okay, cool.

**[07:28] Samarjit (mic):** Yeah. So what's left to do is sort of building out the wiki data, a Google info panel. I can collaborate with Scott on that just to get the details of that. Right. So this is, this is all third party stuff. So we would create, like, a wiki data page. We would have the right information for the Google info panel. And we would also, I'm curious to hear your thoughts on how we can deal with the negative third party reviews. We can. One way to do that is just sort of reply to the reviews on bbb trust pilot, Etc.

**[08:04] Samarjit (mic):** That should sort of improve the sentiment.

**[08:07] Samarjit (mic):** But, yeah, I, all of the stuff that can be modified on the website itself is pretty much complete.

**[08:14] Other participant (system audio):** Yeah.

**[08:15] Other participant (system audio):** Certainly replying to them would be great. And we can probably get you access to those sites, our logins to those sites.

**[08:27] Other participant (system audio):** I don't know if I have them immediately, but I know that we can figure it out.

**[08:33] Other participant (system audio):** And then I guess the other way to do it would be.

**[08:36] Other participant (system audio):** To just post new reviews somehow right.

**[08:41] Other participant (system audio):** From other user accounts that are pod reviews.

**[08:43] Samarjit (mic):** Yeah.

**[08:45] Samarjit (mic):** Yeah. A lot of these third party platforms have bot detection software. So we would have to, I would have to research how to get around that if you're posting reviews.

**[08:59] Other participant (system audio):** Yeah.

**[09:01] Other participant (system audio):** Yeah. I mean, it might be good to do a little research and see if there's a way to do it.

**[09:07] Samarjit (mic):** Yeah.

**[09:08] Samarjit (mic):** So none of the changes we've made have gone live, but once they do, we'll start testing to make sure Geo visibility actually has improved and we'll sort of report on the progress. And if we see any issues in terms of visibility not improving, we'll research that and make changes.

**[09:26] Samarjit (mic):** On the github as needed.

**[09:29] Other participant (system audio):** Okay.

**[09:32] Samarjit (mic):** Information that we would sort of need from you. Yeah, these two things are pretty minor, but just wanted to confirm the, how the legacy shipping policy works. As I understand it, that members who joined before April 2025 have a 45 shipping minimum and everyone else has no minimum. Is that, is that correct?

**[09:55] Other participant (system audio):** Yeah, pretty much.

**[09:56] Samarjit (mic):** Okay. Yeah. I just wanted confirmation that.

**[10:01] Samarjit (mic):** Yeah, this is a more technical thing. So for the reviews on the, on the product metadata.

**[10:09] Samarjit (mic):** Would it be possible to provide the storage field name that okendo uses?

**[10:13] Samarjit (mic):** For the, for the average score?

**[10:18] Other participant (system audio):** Try to find that. I actually haven't seen it.

**[10:22] Other participant (system audio):** It's a meta field in the Shopify product listing.

**[10:25] Other participant (system audio):** Right?

**[10:27] Other participant (system audio):** Is that what you're talking about?

**[10:28] Samarjit (mic):** Yeah. Just what the, what the name of that meta field is.

**[10:31] Other participant (system audio):** Okay.

**[10:32] Other participant (system audio):** Yeah, it's there. I noticed it this morning, actually, when I was adjusting a product.

**[10:39] Other participant (system audio):** See if.

**[10:54] Other participant (system audio):** There's a kendo reviews.

**[11:00] Other participant (system audio):** Review count. And then there's also a kendo reviews average rating.

**[11:06] Samarjit (mic):** Okay. Yeah.

**[11:08] Samarjit (mic):** Okay. New reviews. Average rating. Is that underscores.

**[11:11] Other participant (system audio):** And.

**[11:11] Other participant (system audio):** There's no underscores. There's just spaces in between each ward, and they're all capitalized. Kendo reviews, average rating.

**[11:20] Samarjit (mic):** Okay, I'll make a note of that.

**[11:22] Samarjit (mic):** What kind of reviews I record?

**[11:23] Samarjit (mic):** Ed.

**[11:28] Samarjit (mic):** Yeah. So those are just two minor things I wanted to check with you guys, but, yeah, most of the site.

**[11:36] Samarjit (mic):** Specific work is done. And once it's, once you review it and it's moved to production, I can start testing how it influences actual visibility.

**[11:50] Samarjit (mic):** Yeah. Are there any, any questions?

**[11:55] Other participant (system audio):** Scott, what do you need to do to review that and approve it?

**[11:59] Other participant (system audio):** Yeah, no, I'm already started reviewing it. It looks pretty good. I'm just going to create preview theme for and just make sure that, you know, nothing is being seen on the front end.

**[12:11] Other participant (system audio):** And just go through and make sure it looks good. And if it is, then I'll be able to push it.

**[12:21] Other participant (system audio):** Okay. Yeah. If you could, I mean, if it's possible to do that today or tomorrow, that would be ideal. The reason being that I think.

**[12:30] Other participant (system audio):** Probably.

**[12:34] Other participant (system audio):** On Wednesday to probably tomorrow or Thursday is when Julie's going to set up that new product listing for the daily moisturizer with SPF.

**[12:45] Other participant (system audio):** And I'd love to see once this is live, how that new product.

**[12:53] Other participant (system audio):** Setup will, will work.

**[12:56] Other participant (system audio):** Yeah, no problem. Yeah, I don't expect there to be any issues.

**[13:00] Other participant (system audio):** So if it's all good today, I can push it later today.

**[13:03] Other participant (system audio):** Cool.

**[13:04] Samarjit (mic):** Yeah.

**[13:06] Samarjit (mic):** If there happen to be any issues, message me over slack or email and I'll try to address them as quickly as possible before the new product listing comes out on Thursday.

**[13:17] Other participant (system audio):** Also, let me send you like the.

**[13:20] Other participant (system audio):** I guess like the back end title of the meta field.

**[13:24] Samarjit (mic):** Yeah.

**[13:24] Other participant (system audio):** For.

**[13:26] Other participant (system audio):** Because it's, it's actually middle more complicated.

**[13:32] Other participant (system audio):** I'll send this to you on slack right now.

**[13:39] Samarjit (mic):** And, yeah, if you guys want to review this in more detail, I'll send over this PDF as well.

**[13:44] Samarjit (mic):** After this call.

**[13:51] Other participant (system audio):** Sounds good.

**[13:55] Other participant (system audio):** Yeah. And then so we'll go on for 4.2 work over the next couple weeks here.

**[14:06] Samarjit (mic):** So, yeah, we would ideally have a Wikipedia article, a wiki data entry and a Google info panel.

**[14:07] Other participant (system audio):** Okay.

**[14:15] Other participant (system audio):** How does that work? Do you need, do we need any sort of account or anything?

**[14:16] Samarjit (mic):** And then.

**[14:21] Other participant (system audio):** Or do you can go in? I don't really like Wikipedia.

**[14:25] Samarjit (mic):** Wikipedia and wikidata can be edited by third parties.

**[14:29] Samarjit (mic):** So you don't.

**[14:29] Other participant (system audio):** Right.

**[14:30] Other participant (system audio):** Yeah.

**[14:30] Samarjit (mic):** You don't, there's nothing for you to do on your end.

**[14:34] Samarjit (mic):** I guess the only thing I would need your input on is how we should phrase certain things. So I, I'm going to hold off on, like, creating an entire wiki Wikipedia article because I feel like that's a little bit more of a lengthy process, but a wiki data entry can be done in a couple of hours.

**[14:54] Samarjit (mic):** So that I would, I would just, I can show it to Scott over slack before I, like, create anything public.

**[15:02] Other participant (system audio):** Okay.

**[15:03] Other participant (system audio):** And then for Google info panel, do you need our Google login like admin something? How does that one work?

**[15:09] Samarjit (mic):** I, I don't believe so. I think this can be done pretty easily. But if anything comes up, I'll, I'll contact Scott over slack.

**[15:19] Other participant (system audio):** Okay.

**[15:22] Other participant (system audio):** And which.

**[15:26] Other participant (system audio):** Platforms do you need us to try and figure out our login to trustpilot bbb? Any others?

**[15:35] Other participant (system audio):** Reddit, right? Yeah. Okay.

**[15:40] Other participant (system audio):** Okay.

**[15:43] Other participant (system audio):** Yeah.

**[15:46] Other participant (system audio):** Anything else?

**[15:48] Samarjit (mic):** No, I think that covers everything.

**[15:52] Other participant (system audio):** So are you going to send over those files to Scott and you can drop them into our store, those, root level.

**[15:59] Other participant (system audio):** Files.

**[15:59] Samarjit (mic):** Yeah, I'll send them over on slack.

**[16:00] Samarjit (mic):** Yep.

**[16:01] Other participant (system audio):** And then you need like a CDN link for it.

**[16:06] Samarjit (mic):** If I'm sending them over to you, I think you can just modify the liquid templates on Shopify.

**[16:11] Samarjit (mic):** And that should handle it pretty easily.

**[16:14] Other participant (system audio):** You're not able to do that within GitHub.

**[16:17] Other participant (system audio):** Like within the theme files on GitHub.

**[16:20] Samarjit (mic):** No, the theme files are at a higher level, I think. I think the, I think I would need Shopify admin access.

**[16:27] Samarjit (mic):** Modify that.

**[16:29] Other participant (system audio):** All right.

**[16:29] Other participant (system audio):** Yeah. So let's find.

**[16:34] Samarjit (mic):** All right, sounds good.

**[16:37] Other participant (system audio):** Here. Just send them over. Thank you.

**[16:38] Other participant (system audio):** Thanks Samarjit.

**[16:39] Samarjit (mic):** All right.

**[16:41] Samarjit (mic):** Any remaining questions?

**[16:43] Other participant (system audio):** No, no, we're all good.

**[16:44] Samarjit (mic):** All right.

**[16:45] Samarjit (mic):** I'm excited to meet you guys again next week and continue to make progress.

**[16:50] Other participant (system audio):** Sounds good. Take it easy.

**[16:51] Samarjit (mic):** All right. Thank you. Bye.
