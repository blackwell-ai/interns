# Loontogs AI visibility audit — findings and engagement scope

- Date: 2026-06-02
- Granola document id: e7f514df-ca27-490b-ae03-5d161e70006a
- Created at: 2026-06-02T14:41:54.299Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 417 segments

---

## Notes

### AI Visibility Audit Results for Loontogs

- Automated system tested ChatGPT, Gemini, Perplexity recommendations in hiking/outdoor category
- Loontogs largely invisible compared to competitors in AI assistant responses
- AI systems lack understanding of brand’s quality/durability reputation
- Example: “Best hiking boots in Sweden” query - Loontogs not mentioned despite strong market position
- When Loontogs mentioned in prompt, wins 70% share of voice

### Technical Issues Identified

- Missing structured data on website
  - Product listings incomplete
  - No shipping details, return policy, size/materials metadata
  - Missing LLMs.txt and robots.txt optimization
- English language visibility problems
  - No English Wikipedia article
  - Missing English labels in Wikidata
  - Auto-generated Google knowledge panel description
  - Missing key fields: royal warrant, founding info, product details
- Positive finding: No negative review issues (unlike other brands)

### Current Tech Stack & Shopify Migration Challenges

- Current setup: Sanity CMS → Omnium OMS → headless commerce
- Shopify migration blocked by B2B complexity
  - Preorder system for B2B customers (order confirmation after product purchase)
  - Shopify B2B templates don’t fully support preorder workflows
  - Custom OMS integration required (standard Omnium-Shopify integration failed)
- Migration would require: frontend rebuild, custom integrations, data migration

### Proposed 30-Day Engagement

- Fix product metadata and structured data issues
- Requires CMS access to rewrite website metadata
- Potential to include HealthSport (17 products, same technical backbone)
- Fee structure included in shared document

### Next Steps

- Client reviewing proposal with team
- Follow-up meeting scheduled for next Wednesday afternoon
- Client will send available times after reviewing schedules
- Note: Meeting participants traveling to West Coast for summer

---

Chat with meeting transcript: [https://notes.granola.ai/t/7379515d-9378-46b1-9a9a-25ca96b1d9a2](https://notes.granola.ai/t/7379515d-9378-46b1-9a9a-25ca96b1d9a2)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** And Yeah. Join the meeting. The meeting. Bro, you didn't send the link. I did. I sent it, like, twice. On what? On email. I see. You should attach the She joined.

**[00:29] Other participant (system audio):** Hey there. Hey there.

**[00:34] Samarjit (mic):** Hi. How are you doing?

**[00:34] Other participant (system audio):** Good. Thanks. How are you?

**[00:35] Samarjit (mic):** Doing great.

**[00:36] Other participant (system audio):** Awesome.

**[00:39] Samarjit (mic):** I think we're just waiting on Arman. I think he'll be here in a second.

**[00:42] Other participant (system audio):** Sounds good. I saw you just sent over a document. Thank you.

**[00:47] Samarjit (mic):** Yeah.

**[00:47] Other participant (system audio):** I just opened it up. On the side.

**[00:51] Samarjit (mic):** K. Yeah. He's here.

**[01:00] Other participant (system audio):** Hi. Hey there. How's it going? Oh, good. How are you? Good. Thanks.

**[01:09] Samarjit (mic):** Yeah. So we essentially just ran an audit for, Loontogs. On the geo visibility side. And we wanted to just go over, the findings that we made

**[01:22] Other participant (system audio):** Fantastic. Cool. Fun.

**[01:22] Samarjit (mic):** using our automated system. So I can share my screen, and we can just go

**[01:27] Other participant (system audio):** Yeah. Sounds great.

**[01:30] Samarjit (mic):** through it. Alright. Is everyone able to see my screen?

**[01:42] Other participant (system audio):** Gotcha.

**[01:44] Samarjit (mic):** Okay. So, yeah, this is just an AI visibility audio, essentially how ChatGPT Gemini Perplexity, etcetera, recommend products in your category and how Loon Dogs has visibility to these AI engines. So, essentially, what we did is, we had an automated system where, we had ChatGPT and other LMs, We sort of queried them several times, and we measured the percentage of times that ChatGPT or, these other chatbots essentially talked about LunTogs or mentioned LunTogs in some of their answers. And what we found was that, in a lot of these queries, Loontogs was sort of invisible compared to a lot of, other competitors that we cited over here. And that also that the AI did not the AI assistants did not have insight into sort of the quality of the products that Loondogs has? Because as I understand it, this brand is known for a lot of high quality products that last, like, a really long time. And I don't think the AI systems, understood understood that aspect of the brand, and they weren't communicating it. Clearly.

**[03:05] Other participant (system audio):** Really interesting.

**[03:05] Samarjit (mic):** So

**[03:06] Other participant (system audio):** By the way, you mind if we use an AI note taking app? The topic of AI? Is that okay? Is it okay if I use an AI

**[03:13] Samarjit (mic):** Yeah. Yeah. No problem.

**[03:15] Other participant (system audio):** making app?

**[03:15] Samarjit (mic):** Yeah.

**[03:16] Other participant (system audio):** Perfect. Thanks. I'm gonna confirm with you guys. Cool. Really interesting.

**[03:21] Samarjit (mic):** So these were our findings. I can give you a moment to take a look at them.

**[03:53] Other participant (system audio):** Got it. So when we talk about we take the first two to start with. Category and visibility and credent credential and visibility. Basically,

**[04:01] Samarjit (mic):** Yeah.

**[04:03] Other participant (system audio):** what that means if I get it straight, we're not we're not

**[04:06] Samarjit (mic):** Yeah.

**[04:06] Other participant (system audio):** as visible as we should be. In terms of either the category or when it comes to credibility within the category.

**[04:09] Samarjit (mic):** Yes. So for example,

**[04:17] Other participant (system audio):** Mhmm.

**[04:18] Samarjit (mic):** here's an example prompt that we tested out. This was what said for best hiking boots in Sweden.

**[04:24] Other participant (system audio):** Yep.

**[04:28] Samarjit (mic):** It lists out a bunch of examples. But Lunox is not present in them.

**[04:32] Other participant (system audio):** Got it.

**[04:33] Samarjit (mic):** And then

**[04:34] Other participant (system audio):** Clear.

**[04:35] Samarjit (mic):** we just have a system where we tested out a bunch of variations of these types of problems.

**[04:38] Other participant (system audio):** Makes sense?

**[04:40] Samarjit (mic):** And recorded the the results.

**[04:45] Other participant (system audio):** And then what's this this, part up top of Lindauk's wins 70% share of voice? If we go back to that last page. Share a voice. All 20 Lend wins when named.

**[05:00] Samarjit (mic):** Yeah.

**[05:00] Other participant (system audio):** Got it. Clear. Okay. So this is where the brand doesn't have pull. Within a without the brand. So, of course,

**[05:06] Samarjit (mic):** Yeah. So sort of what that's saying is that when LUNDAG is in the prompt, then it's recommended.

**[05:09] Other participant (system audio):** yes. Makes sense.

**[05:13] Samarjit (mic):** But

**[05:13] Other participant (system audio):** Otherwise, it's it's

**[05:14] Samarjit (mic):** if someone

**[05:15] Other participant (system audio):** Makes sense.

**[05:15] Samarjit (mic):** yeah.

**[05:19] Other participant (system audio):** Then I suppose the question is what leads to that? Where where are we missing information? That would help us to get recognized?

**[05:26] Samarjit (mic):** Yeah.

**[05:28] Other participant (system audio):** Within

**[05:30] Samarjit (mic):** Sort of what causes that is the data on your website.

**[05:33] Other participant (system audio):** Yep.

**[05:35] Samarjit (mic):** So a lot of these LMs, they pull they they scrape the web, and they specifically try to query your website.

**[05:40] Other participant (system audio):** Yep.

**[05:42] Samarjit (mic):** And they look for things such as, complete product listings, metadata, things such as LMs, TXT files, robots, TXT files. So a lot of this just has to be organized correctly.

**[05:51] Other participant (system audio):** Yes.

**[05:54] Samarjit (mic):** On the websites and for the LMs to recommend that. So this this page sort of details that. So the PEPs seem to be missing, structured data such as shipping details, merchant return policy, size of materials. And this sort of makes it harder for the LLM to recommend recommend your website.

**[06:18] Other participant (system audio):** Makes sense. Also likely impacting our SEO as well.

**[06:23] Samarjit (mic):** Yeah.

**[06:25] Other participant (system audio):** Mhmm.

**[06:28] Samarjit (mic):** Another another potential cause of this is that a lot of these a lot of the queries that we did were in English. So I don't think has a English a strong foothold on in English speaking LMs, and this could be caused by things such as a lack of an English Wikipedia article, a lack of English labels or descriptions for, like, Wikidata, We we looked at the knowledge panel, which is essentially Google's representation of the website. And there's a couple fields that are missing information such as a royal warrant. The description seems to be auto generated instead of pulling directly from the website. And these the is it founded by, products produced, country, etcetera, are all missing from the from the Wiki data.

**[07:25] Other participant (system audio):** Which is a lot of our history and heritage.

**[07:26] Samarjit (mic):** Yeah.

**[07:27] Other participant (system audio):** Clear.

**[07:29] Samarjit (mic):** So, So, yeah, these are some things that are already working. The Robusta TXT seems to be fine There are the pages are rendered, on the server side, Bot UA fetches are working correctly. That seems fine. Another thing that we noticed is a lot of the brands that we are working with seem to have a lot of negative reviews off the side, but that's not the case for Lindox, which is nice. So all the work we have to do would only be, fixing the way products the metadata of products is displayed on the website itself.

**[08:07] Other participant (system audio):** Sounds

**[08:08] Samarjit (mic):** Makes So yeah. The this is sort of what we would do during the engagement. To sort of fix the problems that Lindox has.

**[08:18] Other participant (system audio):** Cool. So let's walk through. So this would be adding the product product information.

**[08:25] Samarjit (mic):** Yep.

**[08:28] Other participant (system audio):** So And in order to be set up to to be able to engage in this, what would you guys need? Access to our CMS or

**[08:38] Samarjit (mic):** Yeah. That would that would be required. Essentially, just access to the ability to rewrite the metadata of your website.

**[08:46] Other participant (system audio):** Mhmm. Do you guys have, a code base or, like, another ecommerce platform that you're working with? Then, like, access to that would be great for us. So we're on a headless currently, we're on a headless commerce setup.

**[08:57] Samarjit (mic):** Yep.

**[08:58] Other participant (system audio):** Mhmm. So basically, it's a CMS, which is sanity CMS. Running into a OMS, which is Omnium. And then we are looking into Shopify. Right now. But I would have imagined that if the data isn't included in our current call ProvConnect, is where the the product data is stored. Mhmm. And it's not there in a good way with metadata, in place, then doesn't matter what platform we're on. Right. The data is Okay.

**[09:39] Samarjit (mic):** So, yeah, we can give you time to review this.

**[09:41] Other participant (system audio):** Give me give me

**[09:43] Samarjit (mic):** Like, review this document in detail.

**[09:45] Other participant (system audio):** yeah. Like, give me a little bit of time to review it, and then I see I see you've got the fee in here. I see the thirty day engagement. So let me let me take this back with the team.

**[09:54] Samarjit (mic):** Yep.

**[09:57] Other participant (system audio):** And discuss with them. One question that comes to mind if you guys would consider it, we have two sites. We actually have Lintox and we have HealthSport, and there'd be a question on whether you'd be willing to tackle both. Both sites. You don't have to answer me now. But HealthSport is quite a bit smaller,

**[10:13] Samarjit (mic):** Okay.

**[10:14] Other participant (system audio):** as a brand. We've got, like, 17 products, so it's quite tiny. Also a really fun sandbox for us.

**[10:20] Samarjit (mic):** I think.

**[10:21] Other participant (system audio):** Because

**[10:24] Samarjit (mic):** It's a small.

**[10:27] Other participant (system audio):** Same it's got the same, CMS setup.

**[10:32] Samarjit (mic):** I see.

**[10:33] Other participant (system audio):** So, basically, same technical backbone. I see.

**[10:37] Samarjit (mic):** Alright. Yeah. We'll look into that.

**[10:38] Other participant (system audio):** Yeah. Cool.

**[10:39] Samarjit (mic):** Another

**[10:40] Other participant (system audio):** Awesome. No. No. Go for

**[10:42] Samarjit (mic):** sorry. Go ahead. No. I just wanted to ask a couple questions for you.

**[10:44] Other participant (system audio):** Yeah. Sure.

**[10:48] Samarjit (mic):** Sort of just related to how you guys are organizing your website. So you said you guys were

**[10:51] Other participant (system audio):** That's correct.

**[10:53] Samarjit (mic):** thinking about Shopify. What what sort of what sorts of, like, roadblocks are you seeing in terms of moving your website to Shopify? Why

**[11:04] Other participant (system audio):** So clear it's a very

**[11:04] Samarjit (mic):** isn't this a clear cut decision for you?

**[11:08] Other participant (system audio):** decision that I would like to move. And the reason I would like to to move is because of the headless setup. You guys tell me if I'm telling you things you already know. Mhmm. In order to do any future development, then I need to have developers that are doing that feature development, and I don't have developers. In the team. And so it becomes expensive for us as a small brand.

**[11:24] Samarjit (mic):** Yeah.

**[11:25] Other participant (system audio):** To continue to hire developers to make features. Additions versus Shopify where you've got the whole, basically,

**[11:31] Samarjit (mic):** Exactly. Yeah.

**[11:31] Other participant (system audio):** ecosystem of plugging in different modules and being able to quickly. So for me, coming from a from the background that I do, like, we should be on Shopify, and we should have been on Shopify. The reason that we're not is, in part because of, our b two b business. So we sell both b two c and b two b. And the b to b complexity is is what we need to cater for. For b to c, it's very straightforward. Very, very straightforward. The b to c complexity specifically is that we do preorders. So we sell to customers in advance of them placing orders on the products, and then we confirm those orders

**[12:13] Samarjit (mic):** I see.

**[12:14] Other participant (system audio):** later. Once we've purchased the products. And that's not it's not a straightforward ecommerce purchase.

**[12:19] Samarjit (mic):** And so that's

**[12:21] Other participant (system audio):** In that sense.

**[12:23] Samarjit (mic):** currently hard to do on Shopify.

**[12:26] Other participant (system audio):** Yeah. Exactly. There are some modules that I as I understand it, you can plug in and kinda work around, but it's

**[12:29] Samarjit (mic):** Mhmm.

**[12:30] Other participant (system audio):** it's not Shopify has been more and more developing b to b out of the box, but it's not fully out of the box yet.

**[12:36] Samarjit (mic):** Yeah.

**[12:37] Other participant (system audio):** So Shopify has a b to b I forget what they call them, template effectively. Right? But it's not fully catering for preorders. From the the the analysis that we've done. So far.

**[12:51] Samarjit (mic):** Yeah. That makes sense.

**[12:52] Other participant (system audio):** Have to do sort of workarounds, on that. It's more b two b sales. Like, okay. Retail shop wants to buy your product that's already in stock. And that's that's less flex. So so, anyway, that's that's for me, the decision that the complexity to your question of why I wouldn't do that tomorrow is the integration to the OMS. We need to figure out how we can build that integration.

**[13:16] Samarjit (mic):** As

**[13:18] Other participant (system audio):** And we need to then get the capacity to build it. Mhmm. Put very simply.

**[13:24] Samarjit (mic):** Yeah. That makes sense. Yeah. We were just trying to learn more about Shopify and the difficulties that people have when they're trying to move their websites onto

**[13:31] Other participant (system audio):** Yes.

**[13:32] Samarjit (mic):** onto Shopify.

**[13:33] Other participant (system audio):** Mean, I I think a lot of it is a so I mean, what a high level, what I've understood and be curious what you guys picked up as well is there's the work to basically determine what does the new front end need to look like. Yeah. Actually go build that. And it depends because there are different levels of Shopify. Right? You can do a very templatized easy setup, or you can go all the way to basically using Shopify as your own headless. With a separate CMS, which I've also past lives. So you need to sort your front end. I think that's

**[14:02] Samarjit (mic):** Yeah.

**[14:03] Other participant (system audio):** one thing. It just takes time, and that's also a brand marketing question. What do you want it to look like and feel and blah blah blah blah. Then, the integrations, of basically back to your order management system or your ERP depending on how you

**[14:17] Samarjit (mic):** Yeah.

**[14:18] Other participant (system audio):** set your tech stack up. Because the second consideration. Shopify has a lot of standard integrations for whatever reason with ROMS,

**[14:25] Samarjit (mic):** Mhmm.

**[14:25] Other participant (system audio):** team hasn't been able to get that standard integration to work. So now we have to go build custom. So that's why we've got a little complexity. We have that complexity, I don't know. How it's as deep as I've gone thus far. And then the third, I would believe, would have would have been making sure your data is all in a

**[14:41] Samarjit (mic):** I see.

**[14:41] Other participant (system audio):** good place to be able to to kinda port it over. You guys heard anything else?

**[14:45] Samarjit (mic):** Okay.

**[14:47] Other participant (system audio):** Around Shopify? It's an interesting one because we're we're literally in these good discussions right now.

**[14:51] Samarjit (mic):** Yeah. The Shopify seems to have a very good ecosystem in terms of apps and, like, the variety of different integrations, but a lot of people seem to have, unique setups that make it hard for them to, like, switch over to Shopify.

**[15:01] Other participant (system audio):** Exit.

**[15:04] Samarjit (mic):** And we're just trying to understand exactly why they haven't built those integrations yet.

**[15:08] Other participant (system audio):** Yeah. Yeah. It's interesting. I mean, I think a lot of us are probably where we are, which is on some type of custom build or on some other type of platform, and I think especially true in Europe.

**[15:19] Samarjit (mic):** Yeah.

**[15:21] Other participant (system audio):** Where Shopify has come here. Or people have been late to move to Shopify.

**[15:26] Samarjit (mic):** Yeah.

**[15:27] Other participant (system audio):** Depending on how got it. Cool. Thank you, guys. Really appreciate it. Let me let me take it back with the team. And then, we can be back in touch.

**[15:40] Samarjit (mic):** Alright. Yeah. Sounds good. Is there a time you'd be available to meet next?

**[15:42] Other participant (system audio):** Yes. Probably next week, realistically. I'm gonna also in workshops tomorrow and then in a full day on Thursday, and Friday is a holiday for us.

**[15:54] Samarjit (mic):** Yeah.

**[15:56] Other participant (system audio):** So probably good to touch base towards the middle of next week. Wednesday afternoon, morning time is probably the best best suited.

**[16:09] Samarjit (mic):** Yeah. That should work for us. I think Arman and I will be in Pacific time next Wednesday. So

**[16:19] Other participant (system audio):** It might be very early for you guys.

**[16:19] Samarjit (mic):** yeah. We're going to

**[16:22] Other participant (system audio):** When are you when are you back from Pacific time?

**[16:25] Samarjit (mic):** We're going to be in on the West Coast for the entirety of the summer, so the next couple months. Yeah. That's it.

**[16:30] Other participant (system audio):** You're have to build this, or what's your what's your plan for the summer?

**[16:31] Samarjit (mic):** Yeah. Yeah. Ron and I have been yeah. We were

**[16:34] Other participant (system audio):** On the West Coast?

**[16:36] Samarjit (mic):** going to be going to, like, San Francisco to, like, build out more features for our product. Yeah.

**[16:42] Other participant (system audio):** Very fun. Cool. Yep.

**[16:46] Samarjit (mic):** Yeah, we'll try to find a time that works for for the both of us.

**[16:48] Other participant (system audio):** Yeah. Sounds good. Why don't you guys if you guys wanna look at your your schedules and then let me know and send

**[16:50] Samarjit (mic):** Yeah.

**[16:53] Other participant (system audio):** a few times. Right now, when's my time, my schedule, or potentially Thursday also could be good. So a look, and if you guys want me know, we can take it from there.

**[17:04] Samarjit (mic):** Sounds good. Thank you for meeting with us today.

**[17:05] Other participant (system audio):** Sounds good. Absolutely. Thank you. Thanks, guys. Have a good day. Yep. Bye. Too. Bye.

**[17:10] Samarjit (mic):** Bye.
