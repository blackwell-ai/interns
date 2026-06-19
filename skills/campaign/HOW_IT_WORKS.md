# How the campaign skill works (a plain-language guide)

This guide explains the campaign skill from scratch, assuming you know nothing
about code. If you are twelve years old and have never written a program in your
life, this is written for you. It goes slowly on purpose and explains every word.
If you already know this stuff, the short technical version lives in `SKILL.md`
next door. This file is the long, friendly version.

There are two parts. First, what the skill does and how, step by step. Second, a
deep explanation of the two problems (bugs) we have been fighting, including a
list of common questions and answers for each one.


## Part 1: the big picture

Our company sells a service to other companies. To get a new customer, someone
on our team writes a short, friendly email to a person who works at a company we
think would be a good fit, and asks for a quick call. Sending a first email to
someone who has never heard of you is called cold outreach, and each email is
called a cold email. "Cold" just means there was no warm introduction first.

Doing this by hand is slow. You would have to think of companies, hunt around the
internet for the right person at each one, find their email address, write each
email, send it, and keep a list so you never email the same person twice. The
campaign skill is a robot helper that does all of that for you. You tell it how
many emails you want and roughly who to aim at, and it does the rest.

When you type `/campaign 500` you are telling the robot: go find 500 good people
at 500 good companies, write each of them a personal email, and send them.


## Part 2: words you will need

These words come up over and over. Read them once, then refer back when you get
lost. Each one has a real-world comparison to make it stick.

An API is a way for one computer program to ask another program for something.
Picture a drive-through window at a fast food restaurant. You drive up, speak
your order into the speaker, and a little while later they hand food out the
window. You never walk into the kitchen, and you do not need to know how they
cook. You just place an order and get a result. Every outside service we use
(finding emails, sending email, saving records) has its own drive-through
window, and our program drives up to each one and places orders.

A domain is a company's address on the internet, like `nike.com` or
`glossier.com`. It is the part you would type into a web browser to visit them.

A lead is a person we might email. A good lead is a real person at a real company
who has the power to say yes to us. We often call that person a decision maker,
meaning someone senior enough to make decisions, like a founder or a head of
marketing.

Enrichment is the step where we start with just a company (a domain) and end up
with an actual person and their email address. Imagine you know a company's
street address but not who works there. Enrichment is like phoning the front desk
and asking, "Who runs marketing, and how do I email them?"

A provider is an outside company that does enrichment for us. The two we use are
called Hunter and Apollo. They are like two different phone-book services. You
hand them a company, they hand you back a person and an email. We can pick which
one to use.

Verification means checking that an email address is real and will actually
arrive, instead of bouncing back. A provider gives each email a confidence score
and a status word like "verified." We only keep emails the provider is confident
about, so we do not waste sends on dead addresses.

An LLM is a large language model, which is the kind of artificial intelligence
that can read and write text. Claude, made by a company called Anthropic, is the
LLM we use. You can think of it as an extremely well-read assistant that has read
most of the public internet and can answer questions or make lists from memory.
We use it to make lists of companies that fit who we are targeting.

A token is a temporary pass that proves you are allowed to do something. Think of
a paper wristband at a theme park, or a stamp on the back of your hand at an
event. You show it at each ride or door, and it proves you paid to get in. Two
important things about these passes: you have to show one every single time, and
they expire after a while (the stamp washes off, the wristband is only good for
one day). Tokens matter a lot for the first bug, so keep this picture in mind.

The ledger is our private notebook that records every person we have ever emailed.
Before we email anyone, we check the notebook to make sure we have not contacted
them before. This is how we avoid pestering the same person twice. The notebook
lives in an online database (see the next word), so everyone on the team shares
the same notebook.

Supabase is the online database we use. A database is just an organized place to
store information so a program can save it and look it up later. Supabase holds
the shared ledger notebook and a record of every campaign we have run. To talk to
Supabase, our program drives up to its API window, and it has to show a valid
token (pass) every time.

Gmail is the email service we send through, the same Gmail people use every day.
Our program sends through Gmail's API window using a separate pass that proves we
are allowed to send from our account.

Concurrency means doing several things at the same time instead of one after
another. Picture a kitchen. One cook doing every dish in order is slow. Ten cooks
each working on a dish at once is much faster. When our program sends 8 emails at
the same time instead of one at a time, that is concurrency. It makes things
faster, but as you will see, doing too much at once can also cause problems.

Throttling, also called rate limiting, is when a service deliberately slows you
down or makes you wait because you are asking for too much, too fast. Think of a
highway on-ramp with a traffic light that lets one car on every few seconds so
the highway does not jam. Or a teacher who says, "One question at a time, and you
have asked plenty today, so wait until tomorrow for more." Throttling is central
to the second bug.

A dry run is a practice run where the program does everything except the final,
real action. It finds the people and writes the emails, but it does not actually
send anything. It is like a fire drill: you practice the whole evacuation, but
there is no real fire. We use dry runs to test safely.


## Part 3: the journey, one step at a time

Here is everything that happens, in order, when you start a campaign. Each step
has a short name and then a careful explanation.

### Step 0: you start it

You type `/campaign 500` (or run the `send.sh` script). The number is how many
emails you want. You can also name who sends them and which provider to use, for
example `/campaign 500 samarjit apollo`. This hands the job to the main program,
a file called `run.py`, which conducts the whole orchestra.

### Step 1: preflight checks

Before spending a single credit or sending anything, the program checks that all
its passes work. It confirms we are logged in to the database, that the email
provider's key is present, and that we are allowed to send through Gmail. This is
like a pilot checking the instruments before takeoff. If anything is wrong, it
stops right away and tells you the one thing to fix, instead of failing halfway
through and wasting money.

### Step 2: split the goal across customer types

We do not want all 500 emails to go to the same kind of company. A file called
`icp_mix.toml` lists several customer types (for example direct-to-consumer
brands, warehouses, manufacturers) and how big a slice of the total each one
should get. ICP stands for ideal customer profile, which is a fancy way of saying
"the kind of customer we want." If direct-to-consumer brands get the biggest
slice, most of the 500 will be those, and the rest are spread across the others.
Each customer type also has its own email wording, because what you say to a
clothing brand is different from what you say to a warehouse.

### Step 3: make a list of company websites (the slow step)

For each customer type, the program asks Claude (the AI) to list real company
websites that fit. For example, "list 50 real direct-to-consumer skincare brand
websites." Claude answers from memory with a list of domains.

There is a catch that matters for bug two. Claude gives good answers for the
first 50 or so, then starts repeating famous names, so we ask in small batches
and nudge each batch toward a different corner of the market. We also do these
requests one at a time, never several at once. That sounds backwards, but asking
for several at once actually makes each one slower, for reasons explained in the
bug two section. This one-at-a-time list-making is the slowest part of the whole
process, and it is where the second bug bites.

As each batch of companies comes back, we write it straight to a file (see the
saving section below) and print a short line to the screen. That way you can
watch this slow step make progress, and even measure how fast it is going,
instead of staring at a screen that looks frozen.

### Step 4: find the right person's email at each company (enrichment)

Now we have a pile of company domains but no people. For each domain we ask a
provider to find the decision maker and their email. The two providers work a
little differently.

Hunter does this in one request: hand it a domain, it hands back the most senior
person it knows there, their email, and a confidence number.

Apollo does it in two requests, because Apollo changed how its service works.
First we ask Apollo for the people at that company (it gives us names and job
titles but hides the actual email). Then we point at the one person we want and
ask Apollo to reveal and verify their email. We also double check that the email
it reveals really is at the company we asked about, which throws out stale records
for people who have since changed jobs. Each reveal costs one Apollo credit, so we
only reveal the single best person per company to keep the cost down.

### Step 5: keep only verified emails

Every email a provider returns comes with a confidence score. We set a minimum
bar (80 out of 100). For Apollo this means we only keep emails it marks as
"verified" and throw away ones it only guessed at. This is the verification step.
It is why the people we email actually receive the message instead of it bouncing.

As soon as a verified contact is found, we write it to a file right away (see the
"where things get saved" section) and print it to the screen, so you can watch
the list grow in real time.

### Step 6: check the "already emailed" notebook (the ledger)

For each verified person, we look them up in the shared ledger notebook in
Supabase. If we (or any teammate) have emailed them before, we skip them. We keep
going until we have collected enough brand-new people to hit the number you asked
for. This check is the exact spot where the first bug strikes, because checking
the notebook means talking to Supabase, which requires a valid pass.

### Step 7: write each person a personal email

We have a template, which is an email with blanks in it, like a fill-in-the-blank
worksheet. The blanks are called slots, written like `{{first_name}}` and
`{{company}}`. For each person we fill the blanks with their real first name and
company, so every email reads as if it were written just for them. We make both a
nicely formatted version and a plain-text backup.

### Step 8: send the emails

Now we send, several at a time for speed. For each person, the program does a
careful little dance in this order. First it claims the person in the ledger,
which is an all-in-one "check if anyone has them, and if not, mark them as ours"
action. If someone already had them, the claim fails and we skip without sending.
Only if the claim succeeds do we actually send the email through Gmail. Then we
write down that it was sent. Because the claim and the send happen right next to
each other, two different runs can never accidentally email the same person.

### Step 9: write everything down

After sending, the program records what happened in several places: a row in the
Supabase database, a row in a shared Notion page the team watches, and a local log
file. This way anyone can see how many went out and, later, how many replied.

### Step 10 (later): catch the replies

A separate piece runs once a day. It searches the Gmail inbox for replies from the
people we emailed, uses the AI to guess whether each reply is positive or not, and
updates the database and the Notion page with the reply counts. This is how we
learn which emails are working.


## Where things get saved (so you can find them)

While a campaign runs, information lands in a few places. Knowing where to look is
useful when something goes wrong.

The company websites we generate are written, batch by batch as each one comes
back from the AI, to `skills/campaign/enriched/domains_<id>.csv`, where `<id>` is
a short code printed when the run starts. Each row records the time it was
written, which customer type it was for, and the domain. Because this file fills
up during the slow generation step, you can watch it to confirm the run is making
progress, and roughly how fast, instead of guessing.

The verified people we find are written, one line at a time as they are found, to
a spreadsheet-style file at `skills/campaign/enriched/enriched_<id>.csv`, with the
same short code. This is the live list of emails. Both files live in the same
folder, which is kept private and is never uploaded to our shared code storage,
because it contains real people's contact details.

When we run a logged diagnostic, the on-screen progress is also copied to
`runs/apollo_diag/console.log`, and a structured, machine-readable list of
everything that happened (including any error details) goes to
`runs/apollo_diag/events.jsonl`. These two files are where we look after a crash
to understand what went wrong.

The permanent records (who was emailed, how many, reply counts) live in Supabase
and Notion, which are shared with the whole team.


## Part 4: the two bugs

We have run into two separate problems. They are unrelated to each other and have
different causes. Here is each one in depth.


## Bug 1: the expired pass (the "401 Unauthorized" crash)

### What you see

A campaign runs fine for a while, finding and verifying people, and then suddenly
stops with an error that says "401 Unauthorized." The crash happens during the
step where we check the ledger notebook in Supabase (step 6 above), before any
emails are sent.

### The simple version

To talk to the Supabase database, our program needs a valid pass (a token).
"401 Unauthorized" is the database's way of saying, "I do not accept this pass,
so I will not let you in." So at some point during the run, the pass our program
was holding stopped being accepted, and the database turned it away.

### The deeper version

When the campaign starts, it goes to the front desk once and picks up a pass.
That pass is good for about an hour and then expires, the same way a hand stamp
fades or a day wristband stops working at midnight. The original program made one
mistake: it picked up a single pass at the very start and then tried to use that
same pass for the entire run, no matter how long the run took. It never went back
to the front desk for a fresh one.

A run that finds 1000 people takes a long time. If the run lasts longer than the
pass is good for, then partway through, the pass expires. The very next time the
program tries to check the notebook, the database looks at the expired pass and
says "401 Unauthorized," and the whole run falls over.

### Why we are not completely sure

Here is the honest part. When we tested the pass by itself, right after a crash,
it still worked and still had plenty of time left on it. And both crashes happened
around the twenty minute mark, which is sooner than a fresh one-hour pass should
expire. So the "the pass simply ran out of time" story does not fully fit. The
pass the run started with may have already been old when the run began, or there
may be a small clock disagreement between our computer and the database about
exactly when the pass expires, or the real cause could be something we have not
spotted yet. We have a strong leading suspicion (the pass going stale), but we
have not proven it beyond doubt, which is why we added detailed logging to catch
it red-handed on the next run.

### What we changed to fix it

The fix is simple to say. Whenever the database rejects the pass with a
"401 Unauthorized," the program now goes back to the front desk, gets a brand new
pass, and tries the exact same request again with the fresh pass. We checked, and
a brand new pass always works. So even if we are wrong about the exact reason the
old pass was rejected, getting a new one and retrying fixes it, as long as the
trouble is about the pass at all. We also made sure that if many requests fail at
the same moment, they do not all stampede the front desk at once and trip over
each other, and we added logging so the next failure records exactly what the
database said and how much time the pass had left.

### Frequently asked questions about bug 1

Question: What is a token, really, and why would it expire on purpose?

Answer: A token is a small secret string of letters and numbers that proves the
program is logged in and allowed to act. Services make tokens expire on purpose
for safety. If a token never expired and someone stole a copy, they could use it
forever. By making tokens last only about an hour, a stolen one becomes useless
quickly. The downside is that long jobs have to remember to get a fresh token
before the old one runs out, which is exactly the thing our program forgot to do.

Question: If the token is the problem, why did it work when you tested it alone?

Answer: Because by the time we tested it, either it had been refreshed in the
background, or we were holding a newer one than the run had. A token can be valid
when you check it at 3:05 and rejected when the run used an older copy at 2:50.
Testing it after the fact is a bit like checking whether a milk carton is fresh
the day after someone complained it was sour; the carton you are holding now may
not be the one that caused the problem. This mismatch is exactly why we could not
fully confirm the cause and why we are gathering live logs instead of guessing.

Question: Could this bug cause us to email someone twice, or delete anything?

Answer: No. The crash happens during the checking step and simply stops the whole
run. It does not send anything and does not erase anything. On top of that, the
actual sending step does its own fresh check against the notebook for every single
person right before sending, and if the database cannot be reached at that moment,
the send stops rather than guessing. So a person can never be emailed twice
because of this. The worst this bug does is halt a run early.

Question: Why did your first attempt at a fix not work?

Answer: The first fix asked for a fresh token only when our own program believed
the old one was expired, based on its own reading of the clock. But the database
rejected the token while our program still thought it was fine, so our program
decided no refresh was needed and handed back the same rejected token. The new
fix removes that judgment call: the moment the database says no, we force a
genuinely new token from the front desk regardless of what our clock thinks, and
retry. That sidesteps any disagreement about timing.

Question: Is this Supabase's fault or ours?

Answer: It is ours. Supabase did the correct thing by refusing a token it
considered invalid; that is its job, and we would not want it to accept stale
passes. The mistake was in our code, which grabbed one pass at the start and
reused it for too long without ever refreshing it. The good news is that a
mistake in our own code is a mistake we can fix, which we have.


## Bug 2: the slow company-list step (LLM throttling)

### What you see

A campaign starts, prints that it is generating company lists, and then seems to
crawl. After many minutes, sometimes nearly an hour, it has barely produced any
contacts and has not reached the enrichment or sending steps at all. Nothing has
crashed; it is just painfully slow.

### The simple version

The step that asks Claude to make lists of companies is running far slower than
normal. Each request to Claude, which usually takes around twenty seconds, is
taking a minute or two instead. Because we make many of these requests one after
another, and each is slow, the whole front end of the process bogs down. The most
likely reason is that we have asked Claude to do so much today that Anthropic is
deliberately slowing us down, which is called throttling.

### The deeper version

We do not pay Anthropic for each individual Claude request. Instead we use a
flat-rate subscription, the same kind of plan a person uses when they chat with
Claude all month for one monthly price. A subscription like that comes with usage
limits, because the company has to share its computers fairly among everyone on
the same kind of plan and stop any single user from hogging the machines. Think of
an all-you-can-eat buffet that still asks you not to take ten plates at once; you
have paid to eat, but they will gently slow you down if you try to clear the whole
table in one trip.

There are two layers to the slowness. First, we deliberately make the list-making
requests one at a time rather than all at once. This sounds like it would be
slower, but it is actually the faster choice, because when we fire several Claude
requests at the same moment, the subscription throttles them and they all crawl;
sending them one by one avoids that penalty. Second, on top of that, after running
the campaign many times in one day, we appear to have hit a larger daily-ish limit,
so even the one-at-a-time requests are now being slowed down. The first layer is
normal and built in. The second layer is what made today unusually bad.

### What we can do about it

There are a few options, each with a trade-off. We can wait, since these limits
ease over time as our recent usage falls off. We can make fewer requests by
reusing company lists we have already generated instead of asking for new ones
every run, so we spend the slow step only on genuinely new companies. We can skip
the list-making step entirely for a test by feeding in a list of companies we
already have on hand, which lets a test reach the later steps quickly. Or we can
switch the list-making over to a paid, per-request Anthropic key, which has much
higher limits but costs money for each request, a trade-off covered in the
questions below.

### Frequently asked questions about bug 2

Question: Why is Anthropic throttling the searches, and could using an API key fix
that?

Answer: First, a small clarification. The step being throttled is not really a
search; it is us asking Claude to write a list of companies from memory. Anthropic
throttles it because we are using a flat-rate subscription, and subscriptions come
with usage caps so that the shared computers stay fair and available for everyone
on the plan. When we push a lot of requests through quickly, or a lot in one day,
we hit those caps and get slowed down. Using a paid API key, which is a different
billing setup where you pay for each request by the amount of text involved,
would very likely fix the slowness, because per-request keys come with much higher
limits and are not competing in the same shared subscription pool. The catch is
cost: every request would now cost a small amount of money, whereas the
subscription is a flat monthly price. Our team chose the subscription on purpose
to keep costs predictable, so moving the list step to an API key is a real option
but a money decision, not just a technical one. One more note: an Anthropic key
would only speed up the company-list step, because that is the only step that uses
Claude. Finding the actual emails uses Apollo, which is a separate service with
its own key and its own limits, so an Anthropic key would not change that part.

Question: What does throttling actually mean, and why would a company do it on
purpose?

Answer: Throttling means a service intentionally slows down or delays your
requests when you ask for too much too fast. Companies do this to protect their
shared computers. If one user could ask for unlimited work instantly, they could
slow the service down for everybody or run up huge costs. Throttling is the polite
version of "please wait your turn," and almost every online service does it. It is
the on-ramp traffic light that keeps the highway flowing.

Question: Why do you make the company-list requests one at a time instead of all
at once to go faster?

Answer: It feels like doing them all at once should be faster, and for many tasks
it would be. But we measured it, and for this particular subscription, several
Claude requests fired at the same moment throttle each other and each one becomes
slower, so the batch as a whole finishes later than if we had simply gone one by
one. So we deliberately go one at a time. While each list request is running, we
keep the email-finding step busy on companies we already have, so the time is not
wasted; the two steps overlap.

Question: Did running the campaign many times today make the throttling worse?

Answer: Almost certainly yes. Usage limits build up over a window of time. Each
full run makes dozens of list requests, and we ran several full attempts today
while chasing the first bug. All of that usage stacked up and pushed us into a
slower tier. A single run on a fresh day would very likely not feel this slow.

Question: Will simply waiting fix it, and roughly how long?

Answer: Yes, waiting is the most reliable fix, because these limits are measured
over a rolling window and ease as recent usage ages out. The exact wait depends on
which limit we tripped, but giving it a number of hours, or simply trying again
the next day, is the normal remedy. That is why pausing and retrying later is a
sensible plan rather than forcing it now.

Question: Is this bug dangerous, or could it send bad emails?

Answer: No, it is not dangerous. It is purely about speed. The throttled step only
makes lists of companies; it does not send anything. The worst it does is make a
run take a very long time, or make us give up and try later. No wrong emails go
out because of it, and nothing gets broken. It is annoying, not harmful.


## Quick reference

If a run crashes with "401 Unauthorized," that is bug one, the expired pass. The
fix is in place (force a new pass and retry); check `runs/apollo_diag/events.jsonl`
for the recorded details.

If a run is alive but crawling and stuck on the "generating domains" step, that is
bug two, throttling. The remedy is to wait and retry later, or feed in a ready-made
list of companies to skip that step.

If you just want emails sent and you already have a list of verified people, you do
not need the slow list-making step at all; the program can load a saved list and go
straight to sending.

The short technical version of all of this lives in `SKILL.md` in this same folder.
