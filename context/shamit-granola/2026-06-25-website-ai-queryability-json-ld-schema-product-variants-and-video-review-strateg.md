# Website AI queryability — JSON-LD schema, product variants, and video review strategy

- Date: 2026-06-25
- Granola document id: 1c2c3e5b-dfb6-47b5-a946-63b4628b4292
- Created at: 2026-06-25T18:03:07.182Z
- Attendees: Shamit (shamit@tryblackwell.com)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 104 segments

---

## Notes

### Week 1 Audit Findings

- Firewall fix fully deployed: all bots (GPT, Claude, Perplexity) can now query the site
  - Perplexity bot was blocked as of June 18; confirmed working today

- Core infrastructure solid; focus now on incremental AI-queryability improvements

### High Priority Fixes

- Add SKU ID and Global Trade Item Number to JSON-LD product schemas
  - Current schemas have price and offer type but lack these identifiers
  - Root issue: LLMs returning incorrect prices without them
  - Can’t implement manually without access to codebase and proprietary GTIN data

- Add shipping, return policy, and size variant data to product schemas
  - Include merchant return policy and offer validity period
  - “Price valid until” only relevant during sales/promotions, not regular pricing

- Add structured product group variants
  - Currently 12ml and 30ml options appear as unrelated products
  - JSON-LD product group type would let bots recognize them as variants of the same item


### Lower Priority Fixes

- Fix review feed and homepage entity/breadcrumb structure
- Add social retail URLs and image-sharing capability
- Improve Open Graph metadata, sitemap, and guide files
  - Drafted a sample unified sitemap as an alternative to current structure
  - Makes site navigation easier for AI agents


### Next Steps: Re-Audit Plan

- Client will implement changes and notify when live
- Tryblackwell will then run a before/after audit to measure LLM surfacing improvements
- If changes are effective, shift to ongoing optimization pass
- Will also do a rigorous [schema.org](http://schema.org) review to catch anything missed

### GEO Social Proof Experiment

- Hypothesis: AI product recommendations increasingly rely on social proof (reviews, video, Reddit-style content)
- Proposed experiment: aggregate video reviews to boost GEO presence
  - Scrape existing videos online
  - Send product to vetted human reviewers to generate new content

- Client already runs influencer/PR seeding programs; sees overlap with this approach
- Shamit to scrape existing videos tonight
  - Client to share any offline product videos not yet published


### Next Steps

- **Scrape existing product videos tonight** (Shamit)
  Aggregate with any offline videos the client shares to assess GEO social proof experiment.
- **Send detailed recommendation files to client**
  Files cover all fixes in more depth; client passes to engineers for implementation.
- **Run re-audit once changes are live**
  Client will notify when deployed; compare before/after LLM surfacing results.

---

Chat with meeting transcript: [https://notes.granola.ai/t/a58a32a0-6292-46a6-82eb-bbc4e99fa7f8](https://notes.granola.ai/t/a58a32a0-6292-46a6-82eb-bbc4e99fa7f8)

---

## Verbatim transcript

**[00:00] Shamit (mic):** How do you manage this with like pro bro?

**[00:02] Shamit (mic):** No, I had to up dude. I'm so pissed off.

**[00:05] Shamit (mic):** I'll tell you later.

**[00:11] Shamit (mic):** This guy's very late.

**[00:12] Shamit (mic):** Sadly.

**[00:35] Shamit (mic):** I might need your help to extent some stuff.

**[00:37] Shamit (mic):** Yeah, that's fine.

**[02:18] Shamit (mic):** Let me turn Granol.

**[02:21] Shamit (mic):** I've Granolan.

**[02:28] Shamit (mic):** Hi, Shamir. How are you?

**[02:30] Other participant (system audio):** Hey good, how are you?

**[02:31] Shamit (mic):** Doing well? This is Shamit. I don't know if you've met him. He's the fourth member on our team. He's the one that goes to Stanford.

**[02:37] Shamit (mic):** Hey, Samir.

**[02:38] Other participant (system audio):** Cool. Nice to meet you.

**[02:40] Shamit (mic):** Yeah, he like handled like most of the work for this week. So you'll be sharing a screen and going through it.

**[02:46] Other participant (system audio):** Okay, awesome.

**[02:50] Shamit (mic):** Okay, so let me quickly start sharing the presentation we have.

**[03:05] Shamit (mic):** Okay.

**[03:07] Shamit (mic):** Can you hear me fine?

**[03:10] Shamit (mic):** Awesome? Okay.

**[03:11] Other participant (system audio):** Yeah.

**[03:11] Shamit (mic):** So just to sort of summarize changes that were made in the past week post our initial audit. The good news is the firewall fix is fully in so all bots can query the page fully and you know access the data, including the perplexity follow up, which I think occurred in the past week.

**[03:29] Shamit (mic):** Because the last time we checked on June 18th the perplexity bot wasn't able to query the page.

**[03:34] Shamit (mic):** But we tested it just today again and it was so that's good.

**[03:37] Shamit (mic):** So the foundation for the website is solid in terms of core infrastructure. It's very very good but we think based off the past week there are tiny changes that can be made to the website to make it more AI queryable.

**[03:50] Shamit (mic):** So in terms of week one insights, I'm just going to go through everything that we sort of figured out.

**[03:57] Shamit (mic):** So yeah like I said earlier GPT claude reflects all of them can query your website and these are the most important for agent ecommerce.

**[04:06] Shamit (mic):** So we're in a pretty good spot for that.

**[04:10] Shamit (mic):** So just to sort of outline the changes that we discovered in the past week that can require more actionable insight the highest priority one is adding more information to the JSON-LD structures for each of the products.

**[04:23] Shamit (mic):** Specifically the skew ID and the global trade item number because that'll ultimately result in these you know sort of models producing the right price for these products which we saw was an issue in the initial audit.

**[04:38] Shamit (mic):** The second main highest priority fix is offering commerce fields in variant models for different products. So this includes shipping return and sizes so when you know chat GPT is asked about the size or more information about a product it can return accurate answers.

**[04:53] Shamit (mic):** The third and fourth lower priority fixes is fixing things surrounding reviews and homepage entity lists and those sort of breadcrumbs just making the site easier to navigate and adding a sort of table of contents.

**[05:06] Shamit (mic):** Okay so.

**[05:08] Shamit (mic):** Here is what exists right now on the web page on the left for each of the products. It has it has offers, it has the schema.org link at type to the offer making it you know a link to data structure and it has the price and stuff. But the two key parameters that should be added is the skew ID and the global trade item number to you know fix the audit catching engines returning the wrong price for these products.

**[05:36] Shamit (mic):** Does that make sense?

**[05:37] Other participant (system audio):** Okay.

**[05:39] Other participant (system audio):** Yep.

**[05:39] Other participant (system audio):** That makes sense.

**[05:41] Shamit (mic):** And we weren't able to do this you know manually for each of the pages given you know we don't have access to the code paste and the global trade ad number for each of these are mostly proprietary.

**[05:52] Shamit (mic):** But we can also help figure that out and talk more about it later in the meeting.

**[05:59] Shamit (mic):** So the second main big fix is adding more information surrounding shipping return and size variance to each of these data structures.

**[06:07] Shamit (mic):** What exists right now is on the left under each of the web pages.

**[06:11] Shamit (mic):** But if we can add more information surrounding how long the price is valid for a given offer and more shipping details that match with the structure on schema.org and what most e-commerce sites use, we think that it can make the ultimate product offering more valid and more accurate on llms like chat GPT, claude and perplexity.

**[06:33] Shamit (mic):** Especially surrounding the merchant return policy which we think is pretty important.

**[06:40] Shamit (mic):** Yeah.

**[06:40] Other participant (system audio):** Quick question is valid until is that.

**[06:44] Other participant (system audio):** Like if it's just a regular price.

**[06:49] Other participant (system audio):** Yeah, she put like end of the year. Does that mean, I guess that makes sense. But like, I guess what I'm wondering is if it's the regular price and then we're going to do a sale at some point, like how do you handle that? Or do you only input price on if you're running a sale?

**[07:02] Shamit (mic):** I think price valid until it's only valid if like you said a sale is occurring but there's likely more schema data types or parameters that can be inputted if it's just the normal price. So I think this specific example only occurs under a promotion or a sale if that makes sense.

**[07:19] Other participant (system audio):** Okay, cool.

**[07:22] Shamit (mic):** Okay, so in terms of the product grouping.

**[07:26] Shamit (mic):** A lot more information can be added surrounding you know within a product group what are the different products that exist that are of that type.

**[07:35] Shamit (mic):** So right now it's mostly comment structures that exist for like you know a given product. There's a 12 milliliter option and a 30 milliliter option but a JSON structure can be added where there's a literal defined product group type with the different variants beneath it which makes it easier for the bot to crawl through the website look at the overall product group and then isolate oh this is one variant of the product group and this is another variant and they're of the same type.

**[08:02] Shamit (mic):** Rather than thinking that they're two completely different unrelated products if that makes sense.

**[08:08] Shamit (mic):** Yeah, makes sense.

**[08:09] Shamit (mic):** Okay.

**[08:12] Shamit (mic):** So something that's less priority but can be impactful in the long term in making these websites more AI queryable is open graph sitemap and guide files.

**[08:23] Shamit (mic):** So these are basically links that make the overall website a lot easier to navigate.

**[08:30] Shamit (mic):** So it's metadata in the HTML headers that sort of indicate what a website is and the sitemap in specific is sort of a table of contents for the website that the agent can use to make the navigation between them a lot easier.

**[08:45] Shamit (mic):** So on the left is an example of what that HTML header looks like and on the right is an example of what the change if implemented could look like in a more correct format.

**[08:55] Shamit (mic):** Yeah we looked at the sitemap details that we provided and we just like kind of drafted up like a unified like sitemap on sample alternative to that.

**[09:08] Shamit (mic):** Okay, so to sort of summarize what we discovered in week one in terms of the most actionable and most important lower priority changes the highest priority thing that can be implemented is adding the global trade item number and skew ID to each of the products to make it you know more accurate when chat GPT or cloud queries it.

**[09:28] Shamit (mic):** And then second highest priority is adding info on return policies.

**[09:30] Other participant (system audio):** Okay.

**[09:33] Shamit (mic):** So you know people when they ask it about relevant things like how long the offer stands for example or whether it's rechargeable it gives an accurate response rather than hallucinating.

**[09:44] Shamit (mic):** And then the last four lower priority changes but certainly still important in the long term are social retail URLs review feed the ability to share images and then you know the platform why changes like the sitemap and those sort of steps.

**[09:58] Shamit (mic):** So we have a lot of files that we created with a lot more detail than what was in this presentation that we're going to send afterwards, but they're mainly shaped as recommendations since we you know don't have access to the code base or the global trade item number or skew ID numbers. So we can, you know, send you those products or those files and then you can give it to your engineers to deploy those changes more effectively.

**[10:22] Other participant (system audio):** Yeah, it makes sense. I mean, I think you should all be pretty straightforward to put it.

**[10:23] Shamit (mic):** Okay.

**[10:25] Shamit (mic):** So that was yeah sort of everything that we discovered as of week one.

**[10:30] Shamit (mic):** And yeah we sort of followed the kickoff guidelines to isolate what the main priorities were.

**[10:39] Other participant (system audio):** Okay, awesome. Yeah, this looks good. I think we can, we can get these in pretty quickly. I'll update you when they're live. And then I guess, can you just walk me through like what next steps would look.

**[10:52] Shamit (mic):** Yeah that's a great question Arman and I were talking about next steps too but what we think the main thing is is after you you know give us the information about these things going live our first step is going to be to run another audit to compare you know the before and after in terms of how your products surface on these llms and you know whether or not those changes were effective.

**[11:13] Shamit (mic):** And if they were effective then you know the job was mostly done but we're still going to look at a lot of the items we did in the kickoff to see where tweaks can be made and things can be improved. And we're also going to rigorously scan the schema.org document to see if there's anything that we miss surrounding making your web pages more AI visible.

**[11:32] Other participant (system audio):** Awesome? Yeah, that sounds good.

**[11:35] Other participant (system audio):** Cool. So we'll we'll get started on this on our end. I'll update you when it's ready to re-audit and then we can go from there.

**[11:43] Shamit (mic):** Before we end the meeting there was like something I wanted to ask you about so like an experiment we're running is kind of like our vision of like the future of like where like AI and commerce is going which is that a lot of what like AI will depend on to make like these like recommendations will be like social proof.

**[12:00] Shamit (mic):** So kind of like looking into like reviews as well as like videos and information on the internet about people actually using the product and seeing what they think about it.

**[12:09] Shamit (mic):** Like right now like the kind of main like commonality between like all like product recommendations is like reddit or like other platforms like this where people are actually sharing their authentic experiences using the product.

**[12:20] Shamit (mic):** So something we've been like looking into is kind of aggregating a bunch of like video reviews of products for brands and seeing like if this can like help their like GEO presence.

**[12:32] Shamit (mic):** So something that we were thinking about like running an experiment with was getting like branches send over skews to like human reviewers.

**[12:39] Shamit (mic):** And then like we kind of like aggregate a bunch of like videos of these people using the product and detailing their experiences and seeing if this can like help their GEO presence.

**[12:48] Shamit (mic):** Using this is something that like good molecules like might be interested in.

**[12:53] Other participant (system audio):** So in this case.

**[12:56] Other participant (system audio):** We would send product to is this like existing videos or you're saying to like send product to people to generate new videos.

**[13:03] Shamit (mic):** Yeah, so like we're planning on like doing like a making a scraper to scrape like existing videos but also sending products to like new people just to like kind of like test the thesis.

**[13:14] Other participant (system audio):** I think we'd be open to it if some of you were in phone what you're, what you're thinking. I mean, I know there's definitely like YouTube videos out there already. We do some existing, you know, like influencer type partnerships or where we send out PR to folks who are, you know, active on social media. So I could see.

**[13:39] Other participant (system audio):** I can see this playing into that same, same process.

**[13:41] Shamit (mic):** Yeah makes sense yeah if you guys could like provide us an existing videos that you have already that'd be like really helpful.

**[13:47] Shamit (mic):** And then yeah, I guess like the influencer part if you already kind of have that covered then yeah that would be like good as well.

**[13:53] Shamit (mic):** And if not if you want to get like more people we already are like starting to build like a network of like reviewers who we would kind of like vetted and valued it'll like actually like review products and generate like good content.

**[14:03] Shamit (mic):** So yeah.

**[14:05] Other participant (system audio):** Okay.

**[14:06] Other participant (system audio):** Cool. Yeah. So do you.

**[14:11] Other participant (system audio):** What do you think would be the best next piece there?

**[14:14] Shamit (mic):** I can like scrape the videos that you have tonight and then if you could provide me like any videos that like might not be like online or anything that just kind of like showcase your product then we can kind of like aggregate that all together and then see like how to proceed from there.

**[14:29] Other participant (system audio):** Okay, cool. Yeah, sounds good.

**[14:34] Other participant (system audio):** Okay, awesome.

**[14:35] Other participant (system audio):** Well, great. Thanks.

**[14:37] Other participant (system audio):** Appreciate it.

**[14:37] Shamit (mic):** All right.

**[14:37] Shamit (mic):** Thank you. Thank you.

**[14:40] Other participant (system audio):** All right. See you.

**[14:40] Other participant (system audio):** Bye.
