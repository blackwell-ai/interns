# Blackwell x Public Goods

- Date: 2026-06-25
- Granola document id: 877a7202-6a84-4f6d-b346-0916526f5dc2
- Created at: 2026-06-25T18:06:54.359Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu), Ethan Zhou (ethanpzhou@berkeley.edu), Armaan Priyadarshan (armaan.priyadarshan.29@dartmouth.edu), Shamit D'Souza (shamitd@stanford.edu), Michael Ferchak, Scott Burack
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 238 segments

---

## Notes

### YC and Company Update

- Blackwell recently got YC funding, moving to San Francisco in a few days
- Currently working out of a friend’s house; will move to a proper apartment
- Sameer’s company did 500 Startups years ago, applied to YC twice but didn’t get in

### GEO Visibility Work: Results and Issues

- Two major deliverables completed this week:
  - Wikidata entity created for Public Goods (helps Google Knowledge Panel and LLM indexing)
  - Automated visibility audit script built, querying ChatGPT and Claude

- Positive results seen in just one week, with Public Goods recommended favorably across automated queries
- Sameer flagged inaccurate legacy info surfacing in Google AI overviews:
  - Pet food listed as a product category (discontinued ~2023, referenced from 2021 links)
  - Pantry staples still shown (Public Goods is exiting that category)
  - Sugarcane bottles mentioned (now use recycled plastic instead)

- Samarjit to investigate and suppress incorrect product categories from AI overviews
- Sameer asked about adding himself as co-founder to the Wikidata entry (Morgan has moved on)
  - Samarjit will add him; marginal completeness benefit

- New product: Mineral SPF 30 Moisturizer (currently in draft mode, going live soon)
  - Need to confirm it’s cataloged correctly and PDP tags are properly entered


### LLMs.txt and Audit Methodology

- Sameer has an app-generated llms.txt file in addition to the Shopify-generated one
  - Sameer to share the app-generated version in Slack for review
  - No duplication issue: LLMs query the canonical publicgoods.com/llms.txt

- Audit markdown file sent over email with full methodology and results
- Perplexity testing not yet done; pending API setup
- Samarjit to send Claude/ChatGPT screenshots via Slack showing visibility improvements

### Review Strategy and Okendo vs. Bazaarvoice

- Public Goods uses Okendo (~$600/month) for review solicitation and syndication
  - Sends post-purchase emails; also accepts organic reviews
  - Integrates with Google (store-level ratings visible in search)
  - Not on many marketplaces, so syndication breadth is less critical

- Bazaarvoice quoted at $15,000-20,000/year + ~$6,000 setup fee
  - Has a near-monopoly on syndication with retailers like Nordstrom
  - Would only consider switching if expanding to major retail channels

- Sampling program discussion:
  - Not currently done; Sameer sees potential for new product launches (e.g., the SPF moisturizer)
  - Estimated cost: $15-20 per sample (product + fulfillment + shipping)
  - ROI unclear; Sameer to check with Leanne (influencer marketing lead) and Shop My

- TikTok Shop recently set up; strategy is brand awareness (top-of-funnel), not direct sales ROI

### Remaining Tasks and Open Items

- Samarjit to reply to Trustpilot reviews using provided login; post independently unless unsure
- Reddit account logins: Sameer to follow up with Harley (former HR manager has credentials)
- Before/after prompt comparison: run same prompts from ~one month ago to measure GEO improvement
- All other previously identified issues considered resolved

### Next Steps

- **Investigate and suppress incorrect product categories in Google AI overviews** (Samarjit)
  Pet food and pantry staples are no longer sold; these are surfacing from 2021-era links.
- **Confirm Mineral SPF 30 Moisturizer is cataloged and tagged correctly** (Samarjit)
  Product is in draft mode and going live soon; verify PDP tags are properly entered.
- **Share app-generated llms.txt in Slack** (Sameer)
  Samarjit needs to review it alongside the Shopify-generated version.
- **Post Trustpilot review responses using provided login** (Samarjit)
  Post independently if confident; Slack the team if unsure on specific responses.
- **Follow up with Harley on Reddit account credentials** (Sameer)
  Old HR manager may have the logins; Sameer to confirm whether this was resolved.
- **Run before/after prompt comparison to measure GEO improvement** (Samarjit)
  Use the same prompts from ~one month ago and compare against current results.

---

Chat with meeting transcript: [https://notes.granola.ai/t/4bc64c70-2426-4208-a70c-a11e07e84983](https://notes.granola.ai/t/4bc64c70-2426-4208-a70c-a11e07e84983)

---

## Verbatim transcript

**[00:00] Other participant (system audio):** Couple.

**[00:01] Other participant (system audio):** Yeah.

**[00:01] Samarjit (mic):** Hi. How are you doing? Sorry I came a couple minutes late.

**[00:04] Other participant (system audio):** Yeah. No problem.

**[00:06] Other participant (system audio):** What was the. What was the meeting with y combinator?

**[00:09] Other participant (system audio):** About.

**[00:11] Samarjit (mic):** Yeah. So for every company that y comm funds, we had. They had their kickoff over the last two days, so we had to attend their in-person offices, and they had a bunch of talks with, like.

**[00:23] Other participant (system audio):** You guys? You guys actually got into the y commentary program.

**[00:26] Samarjit (mic):** Yeah, yeah, we got funded a couple. Couple weeks ago.

**[00:29] Other participant (system audio):** Very cool. Very cool. Congratulations. That's. That's awesome.

**[00:33] Other participant (system audio):** Congrats. Are you doing the same stuff here or something different?

**[00:35] Samarjit (mic):** Yeah, it's the same GL plus other services that we offer to Brands.

**[00:43] Other participant (system audio):** And you don't have to be out there on their campus.

**[00:49] Samarjit (mic):** We would have to live in SF. So we're going to be moving to San Francisco in a couple of days.

**[00:55] Other participant (system audio):** Nice. Nice.

**[00:56] Samarjit (mic):** Right now, me and my co-founders were working out of one of our friends houses, but, yeah, we'll be moving to. To a natural apartment recent.

**[00:57] Other participant (system audio):** Yeah.

**[01:04] Other participant (system audio):** Cool.

**[01:05] Other participant (system audio):** Yeah. My business partner and I, we did the 500 startups program years and years ago in San Francisco. That was, that was fun. Interesting. We applied to y combinator twice, but we didn't get in.

**[01:12] Samarjit (mic):** Ly.

**[01:16] Samarjit (mic):** Yes.

**[01:20] Samarjit (mic):** Yeah, it's a great learning experience.

**[01:21] Other participant (system audio):** Yeah, they're, they're more Tech software oriented unless consumer goods focused. So.

**[01:26] Samarjit (mic):** Yeah.

**[01:27] Samarjit (mic):** Yeah, I think their focus is, like, mainly on. Yeah, tech startups. So, yeah, that makes sense.

**[01:36] Other participant (system audio):** Are we waiting for anyone else or just.

**[01:38] Samarjit (mic):** No, we can get started.

**[01:39] Other participant (system audio):** Okay, cool.

**[01:40] Samarjit (mic):** So the two major pieces of work we did over the last week was sort of creating a wiki data entity so that lm is pulling from the internet will be able to have a concrete understanding of what public goods is about. This also helps with the Google knowledge panel. And the second major thing was sort of visibility testing, seeing how public goods reputation or recommendations have improved given the work that we did over the last couple of weeks since all of that was pushed to production.

**[02:19] Samarjit (mic):** I can. And also afterwards, I want to run by another idea we had with you for how we can serve brands better.

**[02:29] Samarjit (mic):** So I can share my screen with a document that sort of explains.

**[02:36] Samarjit (mic):** What we did.

**[02:43] Samarjit (mic):** Yeah. So.

**[02:45] Samarjit (mic):** Can everyone see this?

**[02:47] Other participant (system audio):** Yeah.

**[02:49] Samarjit (mic):** Yeah. So essentially, we're in the stage where we're trying to, we're most of the work has been done, basically, and we're trying to assess how much public goods has improved.

**[03:03] Samarjit (mic):** So the, the remaining work that was left to be done was a couple of edits that Scott and I collaborated on over slack, and then we created a wiki data item. So what this sort of looks like is this.

**[03:18] Samarjit (mic):** It's sort of a wiki data is just, it's sort of like Wikipedia, but it's used for sourcing data on, like, Google AI search overviews or for lms. So you just sort of create a label for what public goods is. You create statements. You say it's an instance of a business, what industry it's in, Etc. You provide all this information and that sort of helps it. And you provide references backing that up.

**[03:48] Samarjit (mic):** And that sort of helps you understand, helps lms understand where exactly what public goods is offering.

**[03:55] Samarjit (mic):** So that's one thing that we created. And then I also built a script to sort of assess public goods'visibility. And we've seen Market Improvement.

**[04:08] Samarjit (mic):** So this sort of clarifies that.

**[04:16] Samarjit (mic):** Right.

**[04:16] Samarjit (mic):** Now.

**[04:20] Samarjit (mic):** So I think overall, in terms of we started, we create an automated script to query chat GPT and claude. And that, and we saw market improvement over both of those for a lot of the automated queries.

**[04:35] Samarjit (mic):** We, we ran public goods was being recommended in a positive manner.

**[04:42] Samarjit (mic):** So obviously we have to give it a couple of weeks for.

**[04:48] Samarjit (mic):** Lms to start, like, re-index, re-indexing the information we gave it, but in just one week, seeing this level of improvement is quite useful.

**[04:59] Other participant (system audio):** I did a question in Google just now. I said what it, what is the public goods brand of house products? And there is some inaccurate Legacy information in there.

**[05:13] Other participant (system audio):** It says, for example.

**[05:19] Samarjit (mic):** Yeah. Let me check.

**[05:20] Samarjit (mic):** That.

**[05:22] Other participant (system audio):** So it.

**[05:23] Other participant (system audio):** Says.

**[05:28] Samarjit (mic):** H.

**[05:28] Samarjit (mic):** TML header.

**[05:29] Samarjit (mic):** Looks like. Sorry, you might mute it yourself.

**[05:32] Other participant (system audio):** Yeah. Okay. Can you see the, the screen?

**[05:35] Samarjit (mic):** Yeah, let me pull it up.

**[05:37] Other participant (system audio):** So it says our catalog features everything from personal care and cleaning supplies to pantry Staples, pet food.

**[05:45] Other participant (system audio):** And home goods. We don't sell pet food. We haven't in a very, very long time.

**[05:50] Other participant (system audio):** Pantry Staples.

**[05:52] Other participant (system audio):** Were sort of exiting from that category. So probably good to sort of get those two out of there if there's any way. I mean, there's this, some, some links here.

**[06:03] Other participant (system audio):** From 2021 that they're referencing here.

**[06:09] Other participant (system audio):** And then something else.

**[06:18] Other participant (system audio):** Yeah, I think.

**[06:21] Other participant (system audio):** So this one here, focus on eco-friendly prep packaging. We don't use sugar cane bottles anymore. We use recycled plastic bottles instead.

**[06:33] Other participant (system audio):** So I don't know if that really matters much at all.

**[06:37] Other participant (system audio):** But.

**[06:41] Samarjit (mic):** So I have a couple of questions. So based on this. Yeah, I understand the pet food might be pretty confusing, given that.

**[06:50] Samarjit (mic):** So was there a time where public goods sold pet food or is that just completely.

**[06:53] Other participant (system audio):** Yeah, I mean, back in 2021, just when these, it's, it's referencing these two here. And we did have pet food back then, but it, we probably discontinued those products.

**[07:08] Other participant (system audio):** In 2023.

**[07:09] Other participant (system audio):** I guess.

**[07:11] Samarjit (mic):** So, yeah, I'll, I'll look into that and make sure it's not the Google AI search overview isn't surfacing any incorrect information. As for the, the sugar cane bottles, I think small, inaccuracies like that, it's.

**[07:29] Other participant (system audio):** Matter. I mean, it's historically it is accurate. It doesn't, it doesn't really matter so much.

**[07:34] Samarjit (mic):** Yeah. Yeah. But when it comes to selling products, you aren't offering.

**[07:34] Other participant (system audio):** I think. Yeah.

**[07:39] Samarjit (mic):** Yeah.

**[07:41] Other participant (system audio):** For the wiki data entry, would it help to add me as the co-founder also and then add a, I don't know if it matters since Morgan is now moved on to a new company and I'm still working here if that, that has any effect on the quality of the data or anything like that.

**[08:01] Samarjit (mic):** I can, I can add you. It would, it might help marginally for completeness.

**[08:07] Samarjit (mic):** Yeah.

**[08:12] Samarjit (mic):** Are there any other specific questions you guys had in terms of what problems you guys were facing when you were searching it up, when you're querying chat GPT.

**[08:27] Other participant (system audio):** Not yet. I haven't tested it again.

**[08:29] Other participant (system audio):** The only question, the only thing I have is a few months ago I downloaded this hell and it created another lambs out text file.

**[08:39] Other participant (system audio):** Like now that we've done this work, do we need that? Have you been relying.

**[08:43] Other participant (system audio):** On that as our llms text or do you add your own?

**[08:50] Samarjit (mic):** The, the one that was pre-built by Shopify?

**[08:54] Other participant (system audio):** It is this one.

**[08:56] Other participant (system audio):** Show you.

**[09:04] Samarjit (mic):** Meeting.

**[09:04] Samarjit (mic):** Of our.

**[09:05] Samarjit (mic):** Video review.

**[09:06] Samarjit (mic):** Of.

**[09:13] Samarjit (mic):** Something.

**[09:14] Samarjit (mic):** That we were talking about.

**[09:15] Samarjit (mic):** Was.

**[09:16] Samarjit (mic):** Getting.

**[09:17] Samarjit (mic):** Like,

**[09:17] Other participant (system audio):** So this is the one that it generated. I think.

**[09:21] Other participant (system audio):** It.

**[09:23] Other participant (system audio):** S pretty much all of our products.

**[09:34] Samarjit (mic):** Okay.

**[09:34] Samarjit (mic):** Yeah. Can I see the. Could you copy paste the link for that so I can look at it?

**[09:37] Other participant (system audio):** Yeah.

**[09:41] Other participant (system audio):** Yeah.

**[09:46] Other participant (system audio):** I wonder if we have like multiple going on right now.

**[09:53] Samarjit (mic):** Yeah, there's no problem with.

**[09:56] Samarjit (mic):** There's no issue with duplication because there's a specific link that.

**[10:03] Samarjit (mic):** Lms query. So it would be public goods.comlms.txt.

**[10:13] Samarjit (mic):** For this one, the one that the app.

**[10:16] Samarjit (mic):** Generated, if you could send that over and I can see exactly how that works.

**[10:27] Other participant (system audio):** I see. So this is the one from Shopify.

**[10:30] Samarjit (mic):** Yeah, this is. So the one from Shopify is.

**[10:34] Samarjit (mic):** Sort of the one that I'll be looking at. But do you think you, you could send over the, the one that the app generated?

**[10:39] Samarjit (mic):** So I could take.

**[10:40] Other participant (system audio):** Yeah. I'm going to put it into our select Channel.

**[10:44] Samarjit (mic):** Okay.

**[10:48] Other participant (system audio):** There's a new product that was created yesterday for our mineral SPF 30 moisturizer. I think we were going to double check and make sure that the new product.

**[11:02] Other participant (system audio):** Gets cataloged correctly.

**[11:05] Other participant (system audio):** On.

**[11:06] Other participant (system audio):** In the whatever document that was.

**[11:09] Other participant (system audio):** Right.

**[11:10] Samarjit (mic):** Yeah.

**[11:11] Other participant (system audio):** And that, and that the, the tags on the.

**[11:15] Other participant (system audio):** On the PDP are entered properly.

**[11:18] Samarjit (mic):** I believe the tags were entered properly. The, the script I wrote should automatically.

**[11:25] Other participant (system audio):** Can we confirm that?

**[11:26] Samarjit (mic):** Generate.

**[11:27] Samarjit (mic):** Yeah, I'll confirm that.

**[11:35] Other participant (system audio):** S the name of the product there and the fat mineral SPF 30 moisturizer. It's in draft mode right now. I don't know if it matters or not, but we're going to be putting it live pretty soon.

**[11:50] Samarjit (mic):** Mirrorless pf.

**[11:51] Samarjit (mic):** 30 moisturizer. Okay.

**[12:03] Samarjit (mic):** And if you guys want to see the.

**[12:07] Samarjit (mic):** Details of the audit that I ran using by querying flawed and chat GPT, I'll send over an email right now with the markdown file that contains the audit information.

**[12:24] Samarjit (mic):** So essentially, as you might remember from our first couple of meetings, we had an automated system for running these audits. So this is automatically generated whenever we retest the visibility.

**[12:55] Other participant (system audio):** For trust pilot.

**[12:57] Samarjit (mic):** Yeah.

**[12:58] Samarjit (mic):** You provided the trust pilot and BBB.

**[13:02] Other participant (system audio):** I don't think I did. I get BBB. I forget.

**[13:08] Samarjit (mic):** No, I believe it was just a trust pilot.

**[13:10] Other participant (system audio):** Yeah.

**[13:11] Samarjit (mic):** Actually, I did have a couple of questions I wanted to ask you about in terms of reviews, because one of the new features we're rolling out for some of the brands we're working with.

**[13:23] Samarjit (mic):** If you.

**[13:25] Samarjit (mic):** Re, if you were interested. So I was wondering how public goods sources its reviews.

**[13:30] Samarjit (mic):** On its website and what it uses for syndication across a bunch of these e-commerce platforms.

**[13:38] Other participant (system audio):** We use a company called okendo.

**[13:43] Other participant (system audio):** To solicit and get reviews from customers, and then they sendicate to, I think Google. I'm not sure where else the limited syndication. Like, for example, we're on Nordstrom e-commerce but it's not syndicated there because they only work with one specific reviews company to do the syndication and they're very expensive. So we haven't done it.

**[14:10] Other participant (system audio):** But.

**[14:11] Other participant (system audio):** Yeah. Okendo is the one that we use.

**[14:14] Samarjit (mic):** So does okendo.

**[14:17] Samarjit (mic):** How. How exactly does a kendo generate the reviews? Is it just when people use public goods products, it prompts users to leave a review? Is that the primary?

**[14:26] Other participant (system audio):** Yeah, we, we send out an email soliciting review from the people who purchased the product and anyone can just go and leave a review themselves if they want without that solicitation.

**[14:40] Samarjit (mic):** I see. Zhou has public goods looked into sampling, sending out free samples to users so that they could generate reviews from that.

**[14:50] Other participant (system audio):** No, we haven't, we haven't really done anything like that.

**[14:54] Samarjit (mic):** And is that because you don't see the need for it or that's just something you haven't considered? Is are the reviews that akendo providing sufficient.

**[15:08] Other participant (system audio):** Well, we've gotten, I mean, for our, our core products, we get plenty of reviews, I think.

**[15:15] Samarjit (mic):** Yeah.

**[15:16] Other participant (system audio):** For newer products. I mean, for something like this sunscreen that we're about to launch, I think it would probably be a good idea to do it.

**[15:25] Other participant (system audio):** But what would that process.

**[15:28] Other participant (system audio):** Look like? I mean, I haven't done it before, so I don't know.

**[15:31] Other participant (system audio):** I guess it's similar to, like, Vine on Amazon.

**[15:35] Samarjit (mic):** So we would have.

**[15:39] Samarjit (mic):** A network of reviewers. This would be regular people, perhaps content creators.

**[15:46] Samarjit (mic):** Where who would receive products from public goods and they would essentially review those products, record videos of themselves using this, using those products. This can be used for UGC content and also for the purposes of generating more reviews that you can then syndicate. It would also be useful for GEO.

**[16:07] Other participant (system audio):** Yeah.

**[16:07] Other participant (system audio):** I wonder if we already have the ability to do that through one of our partners, like shop mai or, or the PR agency that we're working with. I should probably ask Leanne about that because she's the one that's in charge of the influencer marketing, and it would sort of fall under, I think, under that.

**[16:27] Other participant (system audio):** Bucket.

**[16:29] Samarjit (mic):** Yeah. I wanted to ask about the cost, the unit economics of this.

**[16:34] Samarjit (mic):** So if you did want to run a sampling program, you would essentially have to send free products to reviewers.

**[16:44] Samarjit (mic):** At scale, do you think this would be economically viable for your business with this?

**[16:49] Other participant (system audio):** I don't know. I mean, it's probably going to be about 15 to 15 to 20 per item that we send out.

**[16:57] Other participant (system audio):** In, in cost of fulfillment, product and shipping.

**[17:03] Other participant (system audio):** So I don't know what the ROI on that looks like or, or if that's, if, if, if sort of 15 to 20 per sample is worth the effort, I just don't know.

**[17:14] Samarjit (mic):** I see. So that would have to be an experiment.

**[17:19] Samarjit (mic):** And in terms of marketing, you use shop mai, which matches with creators.

**[17:27] Other participant (system audio):** For, for, yeah, for influencer marketing. We're using Shop my. I'm not sure what other platform.

**[17:36] Other participant (system audio):** And then we're about to start looking into tick tock. We just set up a tick tock. Tick Tock shop that isn't quite fully functioning, but seems to be almost ready to go, at which point I think we're going to put some money into tick tock and, and think about it as a marketing Channel rather than a sales channel.

**[18:00] Samarjit (mic):** What do you mean by marketing? So sales Channel.

**[18:04] Other participant (system audio):** Like more about brand awareness than necessarily getting a sales ROI on the effort, you know, so sort of more of like a top of funnel type of marketing effort where we're not expecting necessarily to get like three, three to one return on spend or something like that, where we would be lucky and happy to maybe break even with the sales that we generate on Tick Tock. But more importantly, it's just the eyeballs that, that we get seeing the products up there.

**[18:40] Samarjit (mic):** I see going back to a kendo. Yeah, I stumbled upon them when I was, like, sort of working with the metadata of your website.

**[18:48] Samarjit (mic):** Other than review syndication, do they, what else.

**[18:54] Samarjit (mic):** Exactly do they offer you? And what is the pricing structure of that look like?

**[19:00] Other participant (system audio):** It's not expensive, I think, compared to other review platforms. I want to say it's around $600 a month or something. Does that sound right, Scott? Do you know? That sounds right.

**[19:12] Other participant (system audio):** Yeah. Whereas, like, we just looked at bizarre voices and, you know, they're, they're charging, like, I think their quote was 15 to 20,000 per year.

**[19:29] Other participant (system audio):** Plus.

**[19:31] Other participant (system audio):** Plus like a huge setup cost $6,000, like initial implementation fee.

**[19:37] Samarjit (mic):** Yeah. Yeah. Actually, yeah, we've been looking to bizarre voice a lot, too. And, yeah, I think sort of what makes their platform more expensive is on top of that, they also have, like, the sampling that you would have to set up, which would be another, which would be an additional cost.

**[19:56] Samarjit (mic):** I believe. So.

**[19:57] Other participant (system audio):** Yeah. I think, I think what makes them good is that they kind of have a monopoly on syndication with a number of e-comm marketplaces.

**[20:08] Other participant (system audio):** Like Nordstrom.

**[20:09] Other participant (system audio):** S.

**[20:09] Other participant (system audio):** Like, if we want our reviews to show up on Nordstrom, they, we have to use bizarre voice. It is truly a monopoly there.

**[20:10] Samarjit (mic):** Yeah.

**[20:18] Other participant (system audio):** So that's, that's, I think in part why they can charge a lot more. We found that the functionality of okendo is actually better than bizarre voice.

**[20:28] Other participant (system audio):** Though, aside from.

**[20:28] Samarjit (mic):** And is that just because the sort of, like, the retailers and marketplaces that you're working with, a kendo offers that.

**[20:29] Other participant (system audio):** That.

**[20:39] Other participant (system audio):** We're not working with many marketplaces. So the syndication is not really an issue for us.

**[20:45] Other participant (system audio):** Luckily, they do integrate with Google.

**[20:49] Other participant (system audio):** Because that, that part is important that when you search for our products and you see them on Google, that the ratings and reviews show up there and not just for our products, but from our store as, as, as a whole, too.

**[21:03] Other participant (system audio):** So that's important. But because we're not on lots of different Marketplaces, we're not on Walmart and Target and, I don't know, however many other Sephora and etc. Etc. Etc. That syndication is just, it's not as important to us.

**[21:04] Samarjit (mic):** I see?

**[21:05] Samarjit (mic):** So.

**[21:19] Samarjit (mic):** I see. So if you were to sell on these other channels, would, would you switch to bizarre voice, or would you just stick with Dehukendo integrate with those?

**[21:30] Other participant (system audio):** I don't know. I'm not sure it hasn't been an issue or a question for us. If bizarre voice was the only one that provided that and that we're, and if, and if it went to several different channels that were really important for us, then, yeah, of course, we would switch to them.

**[21:47] Samarjit (mic):** Yeah, that makes sense.

**[21:49] Samarjit (mic):** Yeah, those were just a couple of questions I had because we were looking on creating some new features, but, yeah, that was helpful in terms of the GEO. Yeah, I sent over the, the audit methodology, which I guess Scott could look over the audit methodology and results.

**[22:09] Samarjit (mic):** This is like sort of a more detail, like technical description. It's a markdown file of exactly what sorts of visibility test we did.

**[22:20] Samarjit (mic):** I think I can also send over some screenshots over slack of what it looks like for a user who goes on chat GPT or claude in terms of perplexity. We haven't done any test for perplexity yet.

**[22:36] Samarjit (mic):** But I think once we get some API things set up, we could do that as well.

**[22:41] Samarjit (mic):** And then I, I'll look into the Google AI overview when it comes to the pantry foods and pet Staples. And I'll look at the, I'll send over the confirmation for the moisturizer.

**[22:54] Other participant (system audio):** Okay. And are there, are there any other issues then that we identified earlier that you guys identified earlier that still remain to be tackled?

**[23:06] Samarjit (mic):** No, I think.

**[23:07] Other participant (system audio):** Other than the reviews?

**[23:08] Other participant (system audio):** On better business Bureau and Reddit and stuff?

**[23:12] Samarjit (mic):** Yeah, other than the, other than the reviews.

**[23:16] Samarjit (mic):** I think everything has been addressed.

**[23:19] Samarjit (mic):** Speaking of the reviews. Yeah, I know you gave me the trust pilot login. Would you like for me to sort of just reply to.

**[23:30] Samarjit (mic):** Or, like, create some, like, reviews?

**[23:34] Other participant (system audio):** Yeah. I mean, either both, both of those. Yes.

**[23:37] Samarjit (mic):** Do you need me to run by what I say with you?

**[23:43] Samarjit (mic):** Or could I just.

**[23:46] Other participant (system audio):** If you're fairly confident, then, yeah, just go ahead and post something. But if you're unsure, then just slack and we'll answer the question on slack.

**[23:59] Samarjit (mic):** Public goods has a reddit account? I can do that for unread it as well.

**[24:03] Other participant (system audio):** I'll figure that out. I forgot. I'll follow up with Harley. He said our old HR manager has those logins and he was going to check with her, but, and I'm not sure if that happened.

**[24:15] Samarjit (mic):** Okay. Yeah.

**[24:17] Samarjit (mic):** Are there any remaining questions or action items that need to be done?

**[24:22] Other participant (system audio):** No, I think that's, Scott, anything on your end?

**[24:25] Other participant (system audio):** No. I'm also wondering, like, if you have, like, the prompts that you used before the project.

**[24:34] Samarjit (mic):** Yeah.

**[24:35] Other participant (system audio):** And then we can, like, see if, if they did work, if the work, you know, the work that you did did have an effect on their responses there, that would be interesting.

**[24:44] Samarjit (mic):** No, yeah, no, that's definitely a very important part. The audit should have them. And, yeah, that's, that's exactly what we're going to be doing for visibility work. We'll run the same exact prompts that we had before, like a month ago and now and see if it, it actually improved.

**[25:01] Other participant (system audio):** Yes.

**[25:02] Other participant (system audio):** Yeah, that's it from me. Thank you.

**[25:04] Other participant (system audio):** Cool.

**[25:04] Samarjit (mic):** All right, sounds good.

**[25:07] Samarjit (mic):** All right. You.

**[25:08] Other participant (system audio):** See you later.
