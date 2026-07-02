# Good Molecules — AI visibility audit, schema fixes, and citation seeding strategy

- Date: 2026-07-02
- Granola document id: d449adf1-00c9-4850-829f-85d8fb2a9c3b
- Created at: 2026-07-02T19:05:11.897Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 75 segments

---

## Notes

_No AI summary panel was generated for this meeting._

---

## Verbatim transcript

**[00:00] Samarjit (mic):** Queries that we'd like it to.

**[00:01] Samarjit (mic):** And we can go more in detail for that a little bit later.

**[00:05] Samarjit (mic):** And also for Google AI overview and Gemini, good molecules is doing very, very good. It's named as one of the top brands.

**[00:11] Samarjit (mic):** Okay, so getting more granular for another second, here is what we discovered on chat GPT specifically.

**[00:18] Samarjit (mic):** In the original audit for a query that was like best products for getting rid of dark colors on the skin. Good molecules wasn't necessarily a pick that was recommended, and it was only named if someone directly asked about good molecules.

**[00:32] Samarjit (mic):** But in the most recent audit we did for that very same query about, you know, getting rid of dark coloration on the skin, good molecules was ranked number one best overall. And it was primarily recommended for things like best affordable serum under $15 and things in that sort of price range.

**[00:49] Samarjit (mic):** Yeah. And below is a quote from chat GPT specifically sort of, you know, proving that good molecules was effective. And after this call, we're going to spend an even more detailed report about what we discovered. But yeah, this is what showed up on chat GPT in particular.

**[01:06] Samarjit (mic):** And in terms of the props, we're good molecules was doing really, really good on based off of the re-audit. It was, like I said, best affordable dark spot serums for 2026. A lot of alternative, a lot of affordable alternatives to generally expensive counterparts. And yeah, it was a top pick on three of the six engines that we did for the category question. So yeah, that was basically all the good stuff that we discovered.

**[01:32] Samarjit (mic):** But in terms of potential improvements and the gap that we discovered on these AI engines, claude and perplexity in particular, good molecules was absent and it named competitors like the ordinary, for example.

**[01:48] Samarjit (mic):** And our hypothesis for why this happened is in terms of fixes we recommended in schema that can be changed on the website.

**[01:56] Samarjit (mic):** A lot of that has been fixed and implemented it and we've sort of, you know, maxed that part of it out.

**[02:01] Samarjit (mic):** But what cloud and perplexity are doing is that they're building their answers from third party websites, editorials and journalistic sites like claude sites, forbes vetted, derm approved meeting lighthouse, perplexity tied some other journalistic sites too, which most of its, I guess, reasoning comes from, which we think is why good molecules isn't showing up.

**[02:23] Samarjit (mic):** Despite all the fixes that have been made.

**[02:29] Samarjit (mic):** So based off of what we've identified, we think that there are two big fixes and next steps that can be made.

**[02:34] Samarjit (mic):** First, in terms of schema, we think that the reputation of good molecules across different websites like Instagram, Facebook, Twitter, trustpilot should be embedded in the, in the back end sort of the website.

**[02:50] Samarjit (mic):** So a quick schema change that can be made is the same as parameter. You can see it on the left.

**[02:55] Samarjit (mic):** To the header. We can send more details to our engineers.

**[02:58] Samarjit (mic):** But the main goal of this is to unify the reputation of good molecules across the internet, which are sort of scattered right now when people query chat GPT without a really good anchor.

**[03:09] Samarjit (mic):** And another schema change that we think would be a pretty good idea to implement is on the right.

**[03:14] Samarjit (mic):** Which is adding a review object to each of the products on good molecules website, or at least the most, the highest velocity skews.

**[03:22] Samarjit (mic):** Which basically means for some of the reviews, which shows up on the UI, which indicates that a product is good. That can also be added to the back end.

**[03:30] Samarjit (mic):** And it's something that Google recommends for readability and increasing the.

**[03:36] Samarjit (mic):** Sort of visibility of products for websites on their platform.

**[03:40] Samarjit (mic):** So yeah, this is the first big change on a schema level. We'll send more details for what that actually entails to you after the call. So yeah, that'll be a lot more rigorous.

**[03:52] Samarjit (mic):** Yeah, so the second major change that we've been making is we would sort of have to build a third party coverage that these answer engines are citing. So as sham explained before chat GPT perplexity claude, these answer engines are citing these third party sites like Derm approved, Forbes vetted, glamour, etc. To build the recommendations. So what we would recommend in this case is citation seeding. Essentially what this looks like is we have a network of writers, journalists, independent bloggers who we are working with who you're partnered with. And if you could send over free products for them to review and produce content that would then go on these websites that would improve the visibility on these AI platforms specifically for cloud and perplexity, which seem to be citing these third party sites a lot. But we're all, we're obviously open to any alternatives that you might propose if that's too, too expensive.

**[04:51] Samarjit (mic):** For you to.

**[04:53] Samarjit (mic):** On your end.

**[04:55] Samarjit (mic):** Okay.

**[04:56] Samarjit (mic):** No, I think we'd be open to it.

**[04:59] Samarjit (mic):** I just.

**[04:59] Samarjit (mic):** Need.

**[05:01] Samarjit (mic):** So how.

**[05:01] Samarjit (mic):** Would it work? But you guys have a list of people.

**[05:04] Samarjit (mic):** And you would send to them or we send them the product to you and you give it to them like operational play. Yeah. So operationally a good molecules would be shipping the products directly to our network of riders and reviewers. It doesn't have to be that many products. If you have any hero product, any parts are incredibly popular. We would just need to send out those and maybe a couple skews per product. So we can keep the number of products sent small so it's not a big cost burden on good molecules.

**[05:38] Samarjit (mic):** And since these products are the best selling products, good molecules has to offer. It's very likely that there will be a lot of positive reviews on these third party sites.

**[05:49] Samarjit (mic):** Okay.

**[05:50] Samarjit (mic):** Cool.

**[05:52] Samarjit (mic):** Yeah, so for next steps, what would the process look like on your end? We can send a more detailed PDF sort of covering the logistics. But yeah, what would next steps look like on your end for this?

**[06:06] Samarjit (mic):** Let me.

**[06:06] Samarjit (mic):** Just confirm.

**[06:07] Samarjit (mic):** Like we have.

**[06:09] Samarjit (mic):** Like.

**[06:09] Samarjit (mic):** Our marketing team does send out.

**[06:11] Samarjit (mic):** Like.

**[06:11] Samarjit (mic):** PR boxes to.

**[06:15] Samarjit (mic):** You know, people that they identify.

**[06:16] Samarjit (mic):** Already.

**[06:18] Samarjit (mic):** So I think what it would look like is getting this list of folks included.

**[06:24] Samarjit (mic):** On the list of.

**[06:27] Samarjit (mic):** Outgoing PR that we already have. I just need to travel with them to figure out like kind of criteria and budget wise. Roughly how many.

**[06:36] Samarjit (mic):** People are in the network or how many people are you recommending to send out to you so I can just give them a heads up and confirm.

**[06:43] Samarjit (mic):** The ballpark estimate would be maybe between a dozen and two dozen, so maybe 15, 20 products.

**[06:52] Samarjit (mic):** Shouldn't be a problem.

**[06:53] Samarjit (mic):** So I'll.

**[06:54] Samarjit (mic):** Put that. All right, sounds good.

**[06:57] Samarjit (mic):** Okay, yeah, but that sort of basically copyrresolved the insights that we discovered from the re-audit and we'll be thinking proper next steps should be. And yeah, like summerjit said we're going to send more detailed PDF and report detailing everything here.

**[07:10] Samarjit (mic):** In yeah, a lot more rigor.

**[07:15] Samarjit (mic):** All right. Thank you for meeting with us.

**[07:18] Samarjit (mic):** Yeah, I have two other.

**[07:20] Samarjit (mic):** Just quick.

**[07:21] Samarjit (mic):** Things that I had noted down. One was I saw in the.

**[07:28] Samarjit (mic):** Prior pack that you sent about adding like an FAQ section.

**[07:33] Samarjit (mic):** And my question is like we have a like we have good molecules.com help.

**[07:40] Samarjit (mic):** It's not structured as an FAQ section, but it does answer like those near those types of questions in there.

**[07:51] Samarjit (mic):** Do you recommend like do you think that that's sufficient or do you recommend like adding.

**[07:56] Samarjit (mic):** Another FAQ section that just structures it in that question answer style? Is there some benefit to like specifically structuring it like an FAQ versus like.

**[08:08] Samarjit (mic):** Help center kind of thing?

**[08:10] Samarjit (mic):** Or what would you say?

**[08:14] Samarjit (mic):** Yeah, I think structuring it like an FAQ section would be more optimal because I took a look at your help section and it doesn't have any specific queries that people might potentially ask listed on them. So I think structuring it as an FAQ would be more likely to get your brand recommended by answer engines.

**[08:40] Samarjit (mic):** Okay.

**[08:41] Samarjit (mic):** Cool.

**[08:41] Samarjit (mic):** And then the other just quick update is we added the sitemap URL.

**[08:47] Samarjit (mic):** So I think whenever we do like another.

**[08:51] Samarjit (mic):** Crawlers and I think that should show so I just wanted to update you that that got done. And then yeah when you send me the info for the additional like the same as and the reviews we'll work on adding that into the back end. Awesome. All right sounds good.

**[09:09] Samarjit (mic):** Well yeah, thank you both appreciate the yeah thank you for being with us.
