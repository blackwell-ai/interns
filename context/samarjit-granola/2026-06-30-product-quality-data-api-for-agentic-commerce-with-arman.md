# Product quality data API for agentic commerce with Arman

- Date: 2026-06-30
- Granola document id: cfdbba4f-dada-41d3-ba1a-919c43792e9e
- Created at: 2026-06-30T21:30:42.453Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 153 segments

---

## Notes

_No AI summary panel was generated for this meeting._

---

## Verbatim transcript

**[00:00] Samarjit (mic):** The hitchhiker's guide. Do you see this show like Twitter? Yeah.

**[00:04] Samarjit (mic):** Bro. The. The sally. The book is, like, fully AI. Yeah, no, I.

**[00:11] Samarjit (mic):** Dad, like, wrote a book, like, fully with AI as well. Very similar. I want to read it. It's, like, so I want to read it badly.

**[00:22] Samarjit (mic):** I JP edition.

**[00:23] Samarjit (mic):** It's not his last name.

**[00:35] Samarjit (mic):** Hi. How are you doing?

**[00:37] Other participant (system audio):** Good. How are you?

**[00:40] Samarjit (mic):** This is my co-founder Arman.

**[00:44] Other participant (system audio):** Nice to meet you guys.

**[00:44] Samarjit (mic):** Nice to meet you. Nice to meet you.

**[00:47] Other participant (system audio):** Even the current batch.

**[00:49] Samarjit (mic):** Yeah. Yeah. We're doing the summer 26 batch.

**[00:53] Other participant (system audio):** Did it start yet?

**[00:54] Samarjit (mic):** Yeah. I started, like, last week. Yeah.

**[00:57] Other participant (system audio):** How's it been so far?

**[00:59] Samarjit (mic):** It's been great. It's been great. We. We've gone, like, really good advice from our partner as well as the other. The other startups in the batch.

**[01:08] Other participant (system audio):** Who's your Gran.

**[01:08] Other participant (system audio):** Ny?

**[01:08] Samarjit (mic):** Now, Diana.

**[01:10] Other participant (system audio):** Nice. We did. We did so much 2025 and our partner with Jared.

**[01:15] Other participant (system audio):** But yeah, it's a whirlwind, but congrats.

**[01:18] Other participant (system audio):** And good luck.

**[01:19] Samarjit (mic):** Yeah. Thank you. Thank you.

**[01:22] Other participant (system audio):** Tell me what you guys are doing.

**[01:23] Samarjit (mic):** Yeah. So right now, what we're doing is we're collecting a product quality data.

**[01:29] Samarjit (mic):** So we think that in the future, AI agents will be the ones, like, conducting both transactions. So they sort of need a way to choose which products to buy. So we're collecting a lot of preference data, what products users, like what products they dislike and aggregating that into an API that AI agents can use to make decisions about what to recommend and what to buy.

**[01:51] Other participant (system audio):** Very cool.

**[01:52] Other participant (system audio):** How do you get your data?

**[01:55] Samarjit (mic):** Sort of what we're doing right now is we're doing a combination of two things. First, we're scraping the internet for review data. And second, we're sort of building our network of human reviewers who we send free products to. They record their experience using those products. And then we, we sort of aggregate that data.

**[02:17] Other participant (system audio):** What kind of products?

**[02:20] Samarjit (mic):** Right now. We're starting off with, we're partnering with DTC brand. So beauty products like shampoo foundation makeup, stuff like that. But, yeah, we hope to expand to all, all types of products in the future.

**[02:37] Other participant (system audio):** Why do you partner with the brand?

**[02:40] Samarjit (mic):** We need the brand. So the, so the way our, our model works is that brands send over products to reviewers for free. And what they get in return is they get marketing, they get review data, which is a useful for them.

**[02:56] Other participant (system audio):** So is your business model brands pay you?

**[02:59] Other participant (system audio):** And people pay you for the API?

**[03:01] Samarjit (mic):** Yeah.

**[03:01] Samarjit (mic):** Yeah.

**[03:03] Other participant (system audio):** If we wanted to use your API? What would that look like today? Like what data could we get? How much is the cost?

**[03:12] Samarjit (mic):** We haven't decided pricing for the API yet. I think it would be free for a pilot run. And the, the data would essentially just be product quality data layered on top of the data that channel three already collides.

**[03:28] Other participant (system audio):** Okay, so.

**[03:30] Other participant (system audio):** Interesting. I guess are we like the ideal customer?

**[03:33] Other participant (system audio):** For you?

**[03:34] Samarjit (mic):** Actually, that's what I wanted to talk to you about. I wanted to understand more about what does and see if this would be a good fit for us to work together.

**[03:39] Other participant (system audio):** Yeah.

**[03:45] Other participant (system audio):** Yeah, I guess let me tell you, is this what you guys started with, by the way? How'd you come up with this idea?

**[03:51] Samarjit (mic):** Yeah, we've been working in agent commerce for a while, and this started off as sort of a Creator Network where we were just shipping free products to evaluators. And we were sort of taking a cut based on, like, an affiliate commission model. But then we realized that this data could be useful for people building agentic commerce, like shopping agents.

**[04:16] Samarjit (mic):** So that's how.

**[04:18] Other participant (system audio):** Have you been talking to like people building agentic shopping agents as well?

**[04:23] Samarjit (mic):** Yeah, now we have, we have, we've talked to a lot of, a lot of these shopping energy companies.

**[04:27] Samarjit (mic):** Yeah. The one thing is that I feel like a lot of these companies are, like, very early and, like, pretty small as well. So they haven't, like, really, like, figured out, like, a solution to, like, get, like, people to use their platform yet. So, like, they're not, like, sure how they could use our data.

**[04:27] Other participant (system audio):** What did they say?

**[04:39] Other participant (system audio):** It's a bit funny, right? Because I feel like for the agenda commerce platforms, even the ones that are building on top of us, like they want to be a taste engine or recommend the right products or whatever, but it's actually a really, really hard problem.

**[04:49] Other participant (system audio):** Of like what to recommend.

**[04:52] Other participant (system audio):** And I think the promise of agent to commerce is pretty far off in terms of like actually recommending the perfect products. Like I think probably is better than any agent at recommending a product for a person.

**[05:05] Other participant (system audio):** But good that you guys are starting to. I'm always excited when I talk to somebody like you or like.

**[05:12] Other participant (system audio):** A draft kind of solution because those are very needed.

**[05:15] Other participant (system audio):** For sure.

**[05:17] Other participant (system audio):** I guess for us using your API. I think the thing that'd be more interested in than scrape data is like actual human reviews.

**[05:27] Other participant (system audio):** The reason I say that is because we crawl like crazy. Like I think I checked this morning where like the 250th most active bot online.

**[05:36] Other participant (system audio):** Which is a lot of scraping. And so we already scrape reviews like human reviews on the merchants website.

**[05:44] Other participant (system audio):** We don't use that data super well yet, honestly.

**[05:48] Other participant (system audio):** It's kind of hard, especially because like you kind of want to.

**[05:52] Other participant (system audio):** Understand everything that people say about the product.

**[05:56] Other participant (system audio):** But you can't really feed it all into context or like put it into a graph super nicely.

**[05:59] Samarjit (mic):** Yeah.

**[06:00] Other participant (system audio):** So if you guys learn anything over the course of the summer of like once you have this information, like how do you actually.

**[06:05] Other participant (system audio):** Like act upon it at a like, I understand at a micro level like you're at a specific product and you see the reviews, but at a macro level, like how do you rank products that are like good for sensitive skin or good for dandruff shampoo or like very, I don't know, things that you'd want to be able to do for agenda commerce, but like pretty hard to search over. I guess that's something I'd be interested in and something more than just like embedding similarity.

**[06:30] Other participant (system audio):** For the human reviews.

**[06:32] Other participant (system audio):** How many human review products do you have?

**[06:35] Samarjit (mic):** Right now, network is about a thousand reviewers, and we're sending over products to them, and we're trying to, like, grow it as fast as possible. Yeah. I mean, like, we have, like, a, like, very, like, minimal reviews right now are, like, working on, like, growing that number.

**[06:48] Samarjit (mic):** So.

**[06:48] Other participant (system audio):** I do find the people you send products to.

**[06:50] Samarjit (mic):** Yeah, I mean, like, it's like meaning, like, a lot of, like, ugc creators, like, on, like, social media that are, like, looking for, like, gifted product reviews. So there's, like, certain, like, subreddits as well as, like, Twitter and, like, Facebook groups that you can kind of, like, go through.

**[07:02] Other participant (system audio):** Yeah.

**[07:03] Other participant (system audio):** Tell me what was the affiliate thing you were doing before?

**[07:07] Samarjit (mic):** Sort of what we're doing is we were partnering with brands who wanted advertising, so they would give free products to content creators or influencers. The influencers, if they genuinely enjoyed the product, they would make a video of it. And any, any sort of Revenue that, like, video generates, we would take a cut of that.

**[07:26] Samarjit (mic):** Of that.

**[07:27] Other participant (system audio):** You had partnered with the brands on like impact, whatever and then give the creator a link like your own monetizable link.

**[07:27] Samarjit (mic):** So.

**[07:30] Samarjit (mic):** Yeah.

**[07:33] Samarjit (mic):** Yeah.

**[07:36] Other participant (system audio):** Interesting.

**[07:36] Samarjit (mic):** So, yeah, that sort of started off with a couple months ago, and we've been evolving.

**[07:41] Samarjit (mic):** Yeah.

**[07:43] Other participant (system audio):** I think.

**[07:44] Other participant (system audio):** I would want as I said before I guess I want.

**[07:48] Other participant (system audio):** You guys to I want this to work.

**[07:50] Other participant (system audio):** I think a thousand product reviewers is probably not enough for us to like we have like 100 million products. Like I think if we if we started optimizing and we started ranking like what I would like to do.

**[08:00] Other participant (system audio):** Is if we could rank certain products or brands higher with your data, that'd be great. But if it's too small now, then we would have like we would only be recommending, you know, a thousand products everywhere we want to recommend.

**[08:13] Other participant (system audio):** Across a wide array of products rather than just the ones that you've already reviewed.

**[08:18] Samarjit (mic):** Yeah. So, as I understood channel three, what you guys were building was an API that these developers could, could use if they want to sort of monetize their own platforms. Correct.

**[08:31] Samarjit (mic):** So how would, how would this, how would the product quality data fit in there? Like your original use case of where it was, you're creating an education platform and you want to recommend educational products, how it, how would that sort of work?

**[08:48] Other participant (system audio):** Yeah.

**[08:49] Other participant (system audio):** So our customers are building like new AI shopping platforms kind of probably similar to the customers you might have.

**[08:56] Other participant (system audio):** Which are which are. Yeah. So like that kind of a funny use case that I had my last startup before starting this.

**[09:02] Other participant (system audio):** Of like adding a gender commerce to a tutor. But yeah, like our so our customers are building like, you know, stylist, a gift recommendation engines, a agent that can also shop.

**[09:12] Other participant (system audio):** Essentially like if you want to search the web, use channel three. And we try to be like semi neutral infrastructure. So we don't want to have like too much taste or anything like that. But we do want to give relevant products. So like we have, it's actually really hard to know which brands or like good to recommend.

**[09:30] Other participant (system audio):** And to who and when and for what products.

**[09:33] Other participant (system audio):** And so.

**[09:34] Other participant (system audio):** Some of the problem needs to be sold.

**[09:37] Samarjit (mic):** How do you guys, like, find, like, a customer's initiative? Because I feel like the space of, like, people, like, building, like, shopping agents, like, from, like, what we found is, like, pretty, like, small and, like.

**[09:46] Samarjit (mic):** I don't know. It's kind of hard to, like, reach some people.

**[09:48] Other participant (system audio):** Yeah, it's definitely new.

**[09:51] Other participant (system audio):** People honestly find us.

**[09:54] Other participant (system audio):** I think we're lucky that like you can't build the shopping agent with that product data.

**[09:59] Other participant (system audio):** Like there's literally it's the first roadblock you have to overcome. And so I think people find us kind of naturally that way.

**[10:08] Other participant (system audio):** We've been around like a year. We still we did what last year we launched like midway through I see.

**[10:13] Other participant (system audio):** I guess.

**[10:14] Other participant (system audio):** And I think we've had maybe like 2000 developers with us, which is.

**[10:20] Samarjit (mic):** As I would like, of course, it's a new space.

**[10:23] Samarjit (mic):** I would recommend that to you guys that you launch really early, even though it's close to ready. And that was super helpful. Like, people found this right away.

**[10:30] Samarjit (mic):** From watching NYC. So I would honestly strongly recommend just, like, launch anything, even if it's like you're, you're letting, like, you can launch it like it's live and then just, like, let people off, like, a wait list. There's no way that's like, you let in and use it for the first time.

**[10:45] Samarjit (mic):** You know, even a month after they sign up. Yeah.

**[10:47] Samarjit (mic):** And do you guys, like, maybe, like, talk to people, like, building, like, like, for example, like, frontier labs? You're like, oh, how about their own, like, kind of shopping experiences on their platforms?

**[10:58] Samarjit (mic):** We had talked to the frontier Labs. They are.

**[11:03] Samarjit (mic):** Pretty slow.

**[11:05] Samarjit (mic):** To work with.

**[11:07] Samarjit (mic):** Claude is not. You talked to Dotmic a while ago when they said they're doing intensive converse, and then we talked to them. Yeah. Maybe, like, two months ago, and they said they're actually not doing a dental conversation anymore, at least for the time being, obviously, opening is doing the commerce. Microsoft is doing it during the commerce xai. Not really.

**[11:08] Other participant (system audio):** The order.

**[11:23] Samarjit (mic):** Google, yes.

**[11:24] Samarjit (mic):** But I don't think it really needs to work with anybody because the Google and have, like, all the product data in the world, and they have reviews on all their product data. So I think it's mostly.

**[11:32] Samarjit (mic):** Opening up Microsoft and xai that you can target in the labs.

**[11:39] Samarjit (mic):** Unless I miss.

**[11:41] Samarjit (mic):** I would like to give them product data.

**[11:43] Samarjit (mic):** I think, I think you guys will see is that everybody underestimates how hard this kind of data is.

**[11:49] Samarjit (mic):** Like developers will think they could build a scraper for reviews themselves.

**[11:53] Samarjit (mic):** Labs might think they can get this data directly from brands and then they'll realize they can't. Like they're gonna, they're gonna try.

**[12:00] Samarjit (mic):** We've seen that time and time again where developers are like, you guys are too expensive.

**[12:04] Samarjit (mic):** Like, I want to do this in-house like it's gonna cost you so much more to do this yourself and it's not going to be nearly as good.

**[12:14] Samarjit (mic):** School is like serious, serious egos.

**[12:20] Samarjit (mic):** Yeah.

**[12:21] Samarjit (mic):** So.

**[12:22] Samarjit (mic):** Do you know, like,

**[12:22] Samarjit (mic):** What kind of.

**[12:23] Samarjit (mic):** Like, product like chat GPT or like.

**[12:27] Samarjit (mic):** Music right now?

**[12:29] Samarjit (mic):** What kind of product beans? Yeah. How did it go g products to kind of surface their recommendations?

**[12:34] Samarjit (mic):** Google scrapes and then has Google Merchant Center where merchants can upload feeds. And then same for opening. Well, actually, open was scraping Google shopping.

**[12:43] Samarjit (mic):** So they rules like making some changes to try to stop that. And it seems like it's actually kind of working like open a is not, doesn't really show Google product data anymore. OpenAI accepts feeds.

**[12:54] Samarjit (mic):** They set, they've synced all Shopify and salesforce on the way merchants.

**[12:59] Samarjit (mic):** And then you can also submit feeds, but that's in beta.

**[13:02] Samarjit (mic):** So you can't fully get, I think you'll see that maybe you've seen already is a retailers don't even really have feeds to give the labs, which kind of another funny thing where the labs are like, give us your data and the retailers like, we don't have any data to give you. They don't have a clean, you know, formatted Excel or whatever integration to share data with.

**[13:21] Samarjit (mic):** Them.

**[13:22] Samarjit (mic):** Have you talked to other customers outside of developers? Like maybe brands who might want aggregated product information or any other, like, for example, we were looking to, like, hedge funds who might need a lot of this consumer data. Have you looked into any of those?

**[13:39] Samarjit (mic):** Like, customers or.

**[13:42] Samarjit (mic):** Not so much, honestly?

**[13:45] Samarjit (mic):** Yeah, not so much.

**[13:47] Samarjit (mic):** I see. So, yeah, it's mainly, it's mainly developers.

**[13:51] Samarjit (mic):** Being the developers.

**[13:52] Samarjit (mic):** Yeah.

**[13:52] Samarjit (mic):** I see on your website. I'm pretty sure you guys, like, mentioned, like, brands and how you do have, like, an affiliate model. Like, is that.

**[14:00] Samarjit (mic):** Can you explain a little bit how, like, that works? That's.

**[14:03] Samarjit (mic):** Like, some expanding correctly. Yeah.
