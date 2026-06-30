# Blackwell product demo and OpenAI partnership strategy

- Date: 2026-06-26
- Granola document id: 0e377be3-5dc4-4969-8d41-04cc405a17aa
- Created at: 2026-06-26T22:06:07.904Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 81 segments

---

## Notes

Blackwell x OpenAI

### Team and Product Overview

- Team: Samarjit, Ethan, Arman, Samit, from Dartmouth, Stanford, and Berkeley
- Building a platform for DTC brands focused on agentic commerce
- Two core workstreams:
  - GEO: ensuring brand products surface in ChatGPT, Perplexity, Gemini, etc.
  - Product data collection: brands send SKUs to reviewers for 30-60 second videos; data extracted and fed via API to shopping agents and LLMs


### Demo Walkthrough (Blackwell)

- Demo showed API-enhanced product recommendations vs. standard ChatGPT output
- Example: oily/acne-prone skin query, ChatGPT returns generic results; Blackwell returns products tested against specific parameters
- Video layer: showing “people like them” using the product increases conversion likelihood
- Current customers: shopping agent companies using the API directly
- Future vision: ChatGPT queries Blackwell API at inference time for richer recommendations

### OpenAI Contact’s Feedback

- Familiar with GEO space: previously at Forerunner Ventures, looked at Profound, Nevertune, and Evertune
- Main concern: selling into OpenAI as a vendor is harder than building on the platform
  - Suggested exploring a ChatGPT plugin or app as an easier entry point

- Willing to forward materials to the commerce PM (his best contact on that team)
  - Noted PM may be more relevant than researchers for this use case

- Can also help prioritize:
  - Plugin/app placement
  - Internal engineering resources
  - Co-marketing opportunities


### Credits and API Access

- Codex credits confirmed active
- API credits not yet active: contact needs to resubmit the credit application form
  - Must select the API option and create an API org
  - Will receive $50,000 in credits and Tier 5 usage on completion


### Next Steps

- **Send blurb and sample data to OpenAI contact** (Arman)
  He will forward to the commerce PM; include data quality details and dataset samples.
- **Complete API credit application**
  Resubmit form, select the API option, and create an API org to unlock $50K credits and Tier 5 access.

---

Chat with meeting transcript: [https://notes.granola.ai/t/b81a4a6b-67ec-466f-801e-8062f3a6799c](https://notes.granola.ai/t/b81a4a6b-67ec-466f-801e-8062f3a6799c)

---

## Verbatim transcript

**[00:00] Other participant (system audio):** Certainly more events.

**[00:02] Other participant (system audio):** But, you know, we're basically, as much as you want to work with us, we're willing to work with you.

**[00:08] Other participant (system audio):** I see. That's great.

**[00:11] Other participant (system audio):** Awesome. So with that, would love to learn a little bit more about you guys.

**[00:17] Other participant (system audio):** And. Yeah, what. What's going well, what's not going well, what you're building, how I can support you.

**[00:24] Other participant (system audio):** Yeah. So I guess you can kind of start really good introduction. So amar. These are Ethan and Samarjit and Samit is right here.

**[00:33] Other participant (system audio):** So we're from Dartmouth, Sanford and Berkeley, and we're kind of interested in agentic commerce.

**[00:38] Other participant (system audio):** So the future where, like, AI is doing a lot of, like, the shopping and the selling.

**[00:43] Other participant (system audio):** So what we're kind of building right now is a platform for dtc Brands to help ensure that their products are covered by engines like chat GPT and perplexity, Gemini, and the other ones.

**[00:55] Other participant (system audio):** So we're doing a lot of, like, GEO work right now.

**[00:58] Other participant (system audio):** As well as another part of our company is trying to, like, gather, like, data about products.

**[01:06] Other participant (system audio):** So, like, what we were doing is we're trying to get, like, brands to send, like, skus over to, like, reviewers who make, like, a short, like 30 to 60 second video about the product.

**[01:15] Other participant (system audio):** We're trying to see if, like, this can be, like, useful in, like, how, like, llms kind of service product recommendations.

**[01:21] Other participant (system audio):** That makes sense. We also have, like, a demo in case you would like to see that.

**[01:25] Other participant (system audio):** Yeah. I mean, I'd love to see a demo. I'm. I'm somewhat familiar with the GEO space, so I worked for venture fund called forerunner Ventures.

**[01:33] Other participant (system audio):** For. For the last five years.

**[01:35] Other participant (system audio):** And had looked at a bunch of the different GEO companies like profound, never tune. And I, I work with evertune here at openai.

**[01:45] Other participant (system audio):** And. Yeah, a lot. A lot of my, like, earliest Investments were direct to consumer technology companies, and then over time, that transitioned into AI platforms. So anyway, it's, like, familiar with the lay of the land, but love to see how you guys are approaching it.

**[02:02] Other participant (system audio):** Yeah.

**[02:04] Samarjit (mic):** Yeah, I can share a demo just a little bit context before I dive in. Sort of what we're doing is we're collecting a lot of product quality data in service of GEO. So one thing we found is that answer engines are more likely to recommend products if they know which products are trustworthy, which brands are trustworthy. So sort of how we're doing this is we're having the brand send over products to reviewers who sort of review those products. We extract product quality data from that and sort of feed that as an API to shopping agent companies and to llms. So I can share my screen.

**[02:41] Other participant (system audio):** That'd be great.

**[02:46] Samarjit (mic):** Yeah. So if you all can see this.

**[02:49] Samarjit (mic):** This is sort of how it would look like when our ap is implemented.

**[02:56] Samarjit (mic):** So say you have oily, acne prone skin and you want a foundation that lasts the entire day subject to certain constraints. Right now when chat GPT is recommending that product, it does a pretty good job. It does a decent job. It finds a variety of different products that match your tastes, but they're not the exact type of products are suited to your exact set of constraints because chat GPT doesn't have a lot of data about these, the specificities of these products beyond whatever was listed in the PDP or the product listing.

**[03:31] Samarjit (mic):** So under Blackwell, it gives you more optimized recommendations. These are products that were tested specifically for your skin, our database has a lot of data on the specific parameters that you put in your query. Another useful thing we can provide is videos that can help convince buyers to buy this product. We found based on a customer conversations that when people see people like them use the product and rate it highly, they're more likely to convert, which can be much more useful in the product discovery process. So sort of how we're thinking about this is right now we're working with a lot of shopping agent companies and they've been using our API. But the what we're seeing for the future of Blackwell is that this was sort of be an API that chat GPT could use could query at inference time to give better and more robust product recommendations. And yeah, we just wanted to get your thoughts on that.

**[04:35] Other participant (system audio):** Interesting. So it's set up as an API that open AI would use at inference.

**[04:41] Other participant (system audio):** Versus plugin that the end consumer would opt into.

**[04:47] Samarjit (mic):** Yes.

**[04:47] Samarjit (mic):** Yeah.

**[04:51] Other participant (system audio):** I mean, it's definitely very interesting. I know a guy that works on the, the commerce team, so I could, I could run it by him.

**[04:57] Other participant (system audio):** I think it's probably more.

**[05:02] Other participant (system audio):** Just speaking, like, candidly and, and off the top of my mind.

**[05:05] Other participant (system audio):** Like, I think it's probably harder to convince opening eye to buy or use a product than it is to convince any individual.

**[05:15] Other participant (system audio):** Consumer.

**[05:17] Other participant (system audio):** Or, or other, other businesses.

**[05:23] Other participant (system audio):** So, yeah, have you, have you guys explored using, like, a plugin or creating a, a chat GPT app or something like that?

**[05:33] Samarjit (mic):** Yeah. We've looked into those options. I think having an api is sort of best for the end customer experience, which I think would be best for both openai and for us. But yeah, I understand the process would likely take a lot of time.

**[05:50] Samarjit (mic):** And we would probably have to do some pilot runs or talk to people in the ACP team or the shopping team to get their thoughts on that.

**[06:02] Other participant (system audio):** Yeah. So another thing that we were interested in is that, like you said, you know, people running on the commerce side, so we're wondering if maybe you could help us get in contact with researchers on the commerce side of chat or, like, the people who are looking at chat shopping. So we can kind of understand the data that they need and whether or not this would be like a good fit.

**[06:29] Other participant (system audio):** Yeah. If you guys are able to share.

**[06:33] Other participant (system audio):** You know, share, share some more something affordable.

**[06:38] Other participant (system audio):** I can definitely get it in front of them.

**[06:41] Other participant (system audio):** Yeah. And.

**[06:43] Other participant (system audio):** Also to elaborate on that, willing to give, like, sample data or sample data sets.

**[06:49] Other participant (system audio):** So you guys can use it and, like, the quality as well as other things on the data that we gather.

**[06:55] Other participant (system audio):** Cool. Well, yeah, if you could include that in the note, that'd be great. And I can, I can send it.

**[07:01] Other participant (system audio):** Send it over to them. The person I know best on that team is the product manager for commerce.

**[07:07] Other participant (system audio):** Which I, I actually think that might be most relevant.

**[07:10] Other participant (system audio):** To, again, myth rather than research anyways.

**[07:14] Other participant (system audio):** But, yeah, I'm, I'm happy to advocate for you guys. The, the trouble with trying to with, with companies trying to become a customer of open AI is that I have very little control over it.

**[07:27] Other participant (system audio):** Whereas the things that I do have some amount of control over, like, I can try to get you prioritized to be a plugin or an app. I can get you prioritized for engineering resources that we have internally.

**[07:43] Other participant (system audio):** You know, co-marketing and that kind of thing. I can also help with.

**[07:47] Other participant (system audio):** But, yeah, oftentimes selling into orienthropic or Google or whatever just ends up being like a.

**[07:56] Other participant (system audio):** You know, it's a, it's a more, more difficult process than building.

**[08:02] Other participant (system audio):** On the platform, if that makes sense.

**[08:09] Other participant (system audio):** But, yeah, send it over. I'm happy to advocate.

**[08:12] Samarjit (mic):** Yeah, sounds good. Thank you so much. Yeah, we'll send over a short blurb and some sample data that you can forward and.

**[08:20] Samarjit (mic):** Yeah.

**[08:22] Other participant (system audio):** And then.

**[08:24] Other participant (system audio):** Were you guys able to get your credits all right and everything?

**[08:27] Other participant (system audio):** Yeah, I think I redeemed like that. And I see it in the organization. And, yeah, I set up, like, the chat GPT business as well as codex.

**[08:35] Other participant (system audio):** Okay, great. So this is the Arman at tryblackwell.com.

**[08:42] Other participant (system audio):** You know, let me just double check that you got everything.

**[08:48] Other participant (system audio):** Okay. It looks like your codex credits are good to go.

**[08:56] Other participant (system audio):** And looks like your API credits might not be good to go yet.

**[09:02] Other participant (system audio):** So I'll, I'll send, I'll send over the, the credit application.

**[09:07] Other participant (system audio):** Form again.

**[09:09] Other participant (system audio):** Just, just make sure you go through and you, you click on the API option and create a, an API org, and then you'll get.

**[09:16] Other participant (system audio):** You'll get 50,000.

**[09:20] Other participant (system audio):** And you'll also get tier five usage.

**[09:24] Other participant (system audio):** Okay.

**[09:25] Other participant (system audio):** We do.

**[09:26] Other participant (system audio):** Cool. Yeah. Sorry for the credits process. It's been like we released one thing, and then we gave you guys more credits and we had to do a different application, and there's just some.

**[09:38] Other participant (system audio):** You know, some tricky aspects to it.

**[09:45] Other participant (system audio):** Well, cool. Any other questions I can answer for you guys?

**[09:54] Other participant (system audio):** I don't know. I think, like, the only, like, thing that I guess you want to, like, ask you about was, like, who we could talk to. And I think you've kind of given us information about that. So that's pretty much all I had. Okay.

**[10:05] Other participant (system audio):** Cool.

**[10:07] Other participant (system audio):** Well, yeah, look forward to working with you guys. And please do send over that, that email, and I'll forward it along.

**[10:14] Other participant (system audio):** All right. Thank you.

**[10:15] Samarjit (mic):** Thank you.

**[10:15] Other participant (system audio):** All right. Thank you. Thanks, guys.
