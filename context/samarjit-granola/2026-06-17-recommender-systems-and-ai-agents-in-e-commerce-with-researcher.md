# Recommender systems and AI agents in e-commerce with researcher

- Date: 2026-06-17
- Granola document id: 72247d89-55bf-4ebb-8add-0bb192c34277
- Created at: 2026-06-17T06:39:16.639Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 258 segments

---

## Notes

### Pre-LLM Recommender Systems

- Core framing: recommendation as a supervised learning problem
  - Inputs: purchases, clicks, views, listens, scroll behavior, time of day, social signals
  - Learns from historical interactions to predict what a user will engage with next
  - Runtime: model scores items against user profile, blended with popularity and business rules

- Collaborative filtering: the key insight since the 1990s
  - Early models matched individual taste; later models leveraged collective community patterns
  - Cold-start problem (new items with no signal) handled via random promotion, similarity-based retrieval, or exploration/exploitation sampling


### LLMs and Recommender Systems

- Direct ChatGPT-style recommendations (zero-shot) not practical at scale
  - Too slow and costly for millisecond-latency e-commerce serving millions of users
  - Hallucinates products; can’t ingest millions of data points needed for collective signal

- Dominant real-world approach: hybrid models
  - LLM generates semantic embeddings from item text descriptions (“semantic IDs”)
  - Embeddings fed into traditional ranking pipelines, adding world knowledge without replacing them

- Accuracy improvements don’t reliably translate to business value or user satisfaction
  - Spotify example: optimizing for predicted likes kills discovery, which drives retention

- LLMs do unlock explainability at scale: generated pro-point text to persuade or reassure buyers

### Agentic Commerce and the Future of Recommendations

- Fully autonomous purchase agents are technically feasible now; trust is the real barrier
- Key tension: local agent (privacy-preserving) vs. sending user profile to provider (unlocks collective signal)
  - Likely resolution: API-based handoff where agent passes preferences to retailer’s recommender
  - Agent-to-agent negotiation not realistic in the near term

- What matters most for agent effectiveness: user preferences and taste remain central
  - Contextual signals (time of day, recency) matter in specific domains (e.g., news)
  - Trust in the system may ultimately matter more than preference granularity
    - Once users trust the agent, they stop wanting to configure it


- Advertising implications: visual/emotional ads irrelevant to agents
  - Sponsored ranking (like Google’s paid placements) becomes the dominant mechanism
  - If a user-facing UI remains in the loop, traditional ad surfaces survive

- Research wishlist: move from abstract ranking models toward human-interactive, discovery-oriented systems grounded in real-world deployments and metrics

### Next Steps

- Share project context (GEO / agentic commerce startup) with the professor for any follow-up collaboration
- Review the 2010 recommender systems textbook he recommended

---

Chat with meeting transcript: [https://notes.granola.ai/t/12a392a7-6a05-4b18-ba13-45e590920c05](https://notes.granola.ai/t/12a392a7-6a05-4b18-ba13-45e590920c05)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** Hi. How are you doing?

**[00:02] Other participant (system audio):** Hello.

**[00:04] Other participant (system audio):** How are you? Thanks. Yeah. Sorry for missing the call.

**[00:07] Samarjit (mic):** Yeah, no worries.

**[00:07] Other participant (system audio):** Hope you still have time.

**[00:09] Other participant (system audio):** There was no calendar reminder in my outlook.

**[00:13] Other participant (system audio):** So it's not there. I don't see it.

**[00:13] Samarjit (mic):** Yeah. Software doesn't really send a reminder, so, yeah, that's annoying.

**[00:18] Other participant (system audio):** That's good. But you still have time.

**[00:20] Other participant (system audio):** I have a bit of time so we can.

**[00:20] Samarjit (mic):** Yeah, I still have time.

**[00:22] Samarjit (mic):** Yeah.

**[00:23] Samarjit (mic):** Yeah. Just as, like, a brief introduction. So my name is summer jit. I'm a student at dartmouth college in the united states.

**[00:30] Samarjit (mic):** And sort of what i've been working on is i've been trying to think about how advertising will change as AI agents are the ones that perform most of the transactions on the internet as opposed to people. And I took a little tertiary look at some of the research papers you've published in the past, and you have a lot of research on recommender systems, which I was a little curious about wanting to understand a little bit more about that.

**[00:58] Other participant (system audio):** Okay.

**[01:00] Other participant (system audio):** So what do you want to know specifically?

**[01:03] Samarjit (mic):** Yeah. So I guess my first sort of question is i'm familiar with lms and foundation models and how they recommend products, but i'm not as familiar with recommender systems before lms. I've seen, like, you've published a lot of papers in the 2010s, the 2000s recommendation system. So I just wanted to learn a little bit more about what those look like.

**[01:29] Other participant (system audio):** I can recommend this very old book from 2010, which should lay out the main ideas there. So. So.

**[01:37] Other participant (system audio):** It's really surprising that, okay, pre-LLM times, I think it's still there in industry. Most organizations I work with, they don't have llms for recommendations so the technology seems still relevant.

**[01:50] Other participant (system audio):** So.

**[01:53] Other participant (system audio):** I think the main idea is that you frame the recommendation problem as a supervised learning problem. So you have signals like purchases.

**[02:03] Other participant (system audio):** Or item views and listens to songs and then you want to predict from the observed interactions in the past.

**[02:10] Other participant (system audio):** If a given user would listen to this or purchase something.

**[02:13] Other participant (system audio):** And then once this is framed as a supervised learning problem, you can throw all sorts of problems like models on it from logistic regressions to matrix vectorization or deep learning models.

**[02:25] Other participant (system audio):** So the idea is like, okay, you have a given user profile, you observe the user behavior in the past given usually huge lack of what people did. And then you learn a prediction model from the observed behavior.

**[02:39] Other participant (system audio):** And then at runtime when the customer visits, you see what the model would predict for this customer given the historical interactions we observed and maybe also the most recent ones.

**[02:49] Other participant (system audio):** Plus in reality you have other signals like popularity and trendiness.

**[02:54] Other participant (system audio):** Plus business rules in practice that you would apply to obtain the final ranking.

**[02:59] Samarjit (mic):** Okay, so sort of the input data that you look at is what did this person choose?

**[03:06] Samarjit (mic):** In the past? What did people like them choose in the past? And then external things such as popularity.

**[03:13] Samarjit (mic):** Is that correct?

**[03:14] Other participant (system audio):** Yeah, I would say that the main idea is this collaborative or collective behavior, the patterns of the whole community. So the very early models, they really looked at individual users like what I preferred.

**[03:25] Other participant (system audio):** And they recommend like similar stuff. And since the 1990s paper started thinking of, okay, there's a collective behavior collective pattern. So I might also look at if we always have the same taste. And if you find something new that you like, okay, recommend it to me as well.

**[03:43] Other participant (system audio):** That's the some sort of intuition.

**[03:45] Other participant (system audio):** Behind these models. And in terms of the signals that you consider all sorts of significant can be there. So all these web companies, tech companies, they log everything not only purchases, but also clicks scrolling 12 times social signals context like time of the day.

**[04:01] Other participant (system audio):** A number of additional signals could be factored into these models.

**[04:06] Samarjit (mic):** I see. So what about for, so say there's a recommender system for what sorts of products you want to buy, let's say, like shampoo. And there's a new shampoo brand, which is, which hasn't, which has a very small number of customers, hasn't really been tested before. So how does that product get recommended? How do people start discovering that product?

**[04:28] Other participant (system audio):** I think that the problem you refer to is called cold start or cold or warm start. I think you have new objects you have no signals for, no path directions.

**[04:38] Other participant (system audio):** So you can do a mix of things.

**[04:41] Other participant (system audio):** So first you can add business rules to simply promote the randomly throw in these news items into the recommendation list. That's the trivial method to make sure these items get exposure.

**[04:51] Other participant (system audio):** Initial exposure. So that's, I think one thing that probably many businesses do. The other is if there are methods that you could use like a combination of.

**[05:02] Other participant (system audio):** Approaches that use like the collective patterns for which we don't have any signals. But you could also mix in a component in the method that uses these like similarity based retrieval. Like I know for me at least if I had, if I prefer the same brand, I can say, okay, now this I could rank items not only based on popularity in the community because we don't have that signal yet. But also if it's similar to my previous taste and many models also have this idea of.

**[05:32] Other participant (system audio):** Exploration and exploitation as part of their nature of the models. So you randomly show people stuff. Not only stuff which is new on the on the marketplace, but also stuff that's new to them to better understand user preferences. So you risk a bit by showing stuff people might not like, but it helps you explore.

**[05:52] Samarjit (mic):** I see.

**[05:53] Samarjit (mic):** So.

**[05:56] Samarjit (mic):** When, so when we're talking in the context of lms, say you go on chat gbt and you're asking chat gbt to recommend certain products for you, how does, how does everything we talked about change in that context?

**[06:11] Other participant (system audio):** Sorry, what did change? Can you repeat?

**[06:14] Samarjit (mic):** Yeah. So essentially what changes.

**[06:16] Samarjit (mic):** In the context of llms?

**[06:19] Samarjit (mic):** Like.

**[06:22] Other participant (system audio):** Most in academia? So what it has a huge impact of course with L&M. So one, there's different ways. Let's start with this. There's different ways how LLMs are used, the way used for recommendation problems. So the most straightforward way you suggest maybe is just go to chat GPT type in I need, I want to watch this new movie. And here's my what I usually like and then chat GPT and directly gives you something.

**[06:48] Other participant (system audio):** Which would be called zero shot learning. So it just gives you a in context learning gives you some information about what you like.

**[06:56] Other participant (system audio):** So this is, I'm not sure this is used a lot in practice. There's many issues with this like latency. It's too slow to give you at scale recommendation. It's costly of course for other providers. It may hallucinate and give you things that don't exist. So maybe.

**[07:11] Samarjit (mic):** Sorry, why is it, why is it costly? Or why can't it scale?

**[07:16] Other participant (system audio):** You know, if you have an e-commerce site where you serve recommendations to tens of thousands of parallel users, the latency is a few milliseconds to generate the recommendations. So if you use chat gbt know that you know there's latency until the recommendations show up, which is, and if you embed these into websites, yeah, massive will just call back chat GPT in the background. It would be way too slow.

**[07:42] Other participant (system audio):** To render the whole page. And the cost is also, of course, if you run it large scale, either you purchase it.

**[07:42] Samarjit (mic):** I see.

**[07:49] Other participant (system audio):** So it's a lot of token costs involved in background. But again, we talk of thousands of customers a day.

**[07:55] Other participant (system audio):** For small sites or millions for amazon scale. And if you host it by your own, you have the cost of hosting, you need all these specialized hardware.

**[08:04] Other participant (system audio):** To have this at scale. And I don't think it's case at all very well.

**[08:09] Other participant (system audio):** So that's, that's one issue for practical deployments. From the recommendation perspective, I said.

**[08:16] Other participant (system audio):** It hallucinates probably. And it might also not reach the full performance of these traditional models. Because when you feed the context, you can tell the system, okay, this is what I like.

**[08:30] Other participant (system audio):** And then the system chat might find similar movies based on, it's internal knowledge.

**[08:36] Other participant (system audio):** But if you want to have this collective.

**[08:39] Other participant (system audio):** These collective patterns that other machine learning models would identify, you would have to support millions of data points into the context. And that's not how these, and this is not working well.

**[08:52] Other participant (system audio):** So, but instead of this, what happens is what people use.

**[08:56] Other participant (system audio):** Actually is a combination of these traditional models with encodings that you get from llms. So instead of having, okay, I have items that I recommend have just an ID or a skew in e-commerce.

**[09:09] Other participant (system audio):** You take textual description of the item. Like this is a shampoo, blah, blah, blah brand and so on and compress and embedding from it using an llm. And then you use these embeddings as part of the more traditional model.

**[09:22] Other participant (system audio):** Which would be called in semantic IDs.

**[09:25] Other participant (system audio):** Instead of just numerical ideas that we had in the past. And then you add these extra world knowledge that's encoded in the llms into the traditional recommendation retrieval pipeline.

**[09:36] Samarjit (mic):** Yeah, that makes sense.

**[09:38] Samarjit (mic):** So, yeah, in the, in the scenario where all of these product, a lot of this product data is embedded, and then you do vector embeddings or you find, like, the closest embedding for a given, like, query. How does that capture, like, product? Like, is that effective? Like, does that give the best recommendation to the user?

**[10:01] Other participant (system audio):** That opens like the question is what's the best recommendation? It's an academic pretend to have an answer to this, but there is no answer.

**[10:10] Other participant (system audio):** Because it's in reality a multi stakeholder problem. So what's best for the consumer might not be best for the providers. So that passed in the practical sense doesn't really exist in some ways.

**[10:21] Other participant (system audio):** If you just look at academic literature, we try to optimize some abstract computational metric like accuracy or retrieval performance. And then there's a lot of papers that suggest that incorporating this semantic knowledge extracted from llms.

**[10:39] Other participant (system audio):** Into the existing models is beneficial. So there's a lot of claims here. The problem still remains that if you have, let's say, a vector based retrieval, you can increase some recall or precision.

**[10:52] Other participant (system audio):** On the retrieval task, but whether or not these accuracy improvements would translate into business value consumer satisfaction, nobody knows.

**[11:01] Samarjit (mic):** Yeah, it's a little too early to tell.

**[11:03] Samarjit (mic):** I guess.

**[11:05] Other participant (system audio):** Now it's a fundamental problem that these abstract methods, abstract proxies for improvement measurements that you use in data based experiments, whether or not they translate to any value for any of the stakeholders.

**[11:18] Other participant (system audio):** There's no evidence for this. So there's in fact there's a lot of papers that show that if you improve, let's say the prediction accuracy, it might be.

**[11:28] Other participant (system audio):** Worse than other models in reality. Like in spotify, if, if the system constantly recommends your stuff, it knows you will like. Then you have zero discovery.

**[11:39] Other participant (system audio):** But discovery is super important for retention.

**[11:42] Other participant (system audio):** Or just the business model of spotify and others.

**[11:45] Samarjit (mic):** Okay. And so this is, like, in the context of chatbots on websites, right? So this is like, Amazon has their own chatbot on their website, and then it will sort of look at, like, all the product embeddings. But, like, what are your thoughts on people going straight to chat gbt and they ask on chat GPT, like, what's the best shampoo for me? So in that context, chat gbt would just be searching the internet.

**[12:09] Samarjit (mic):** Right?

**[12:11] Other participant (system audio):** It depends on how these, tools or bots are configured.

**[12:15] Samarjit (mic):** Yeah, it can touch the internet.

**[12:19] Samarjit (mic):** I mean, there's different maybe phases of, of the customer Journey. So now if you're just looking.

**[12:26] Samarjit (mic):** At the information search things to understand what kind of shampoo.

**[12:33] Samarjit (mic):** That.

**[12:35] Samarjit (mic):** You want.

**[12:39] Samarjit (mic):** These specific products and the availability of a certain product at the store, but rather what type of.

**[12:44] Samarjit (mic):** Ingredients.

**[12:44] Samarjit (mic):** Whatever.

**[12:45] Samarjit (mic):** So this is not my favorite expertise.

**[12:47] Samarjit (mic):** But I think there's an information gather can help.

**[12:50] Samarjit (mic):** If you.

**[12:50] Samarjit (mic):** Want to.

**[12:53] Samarjit (mic):** Sort of whatever. But then if you're.

**[12:56] Samarjit (mic):** And then here chatbots, I think, can help.

**[12:59] Samarjit (mic):** Like, independent of the catalog.

**[13:01] Samarjit (mic):** Which.

**[13:02] Samarjit (mic):** Is.

**[13:03] Other participant (system audio):** If you have a chatbot embedded on an e-commerce site, I think these chatbots in the background, they don't search the internet, they search the catalog of the shop because availability and delivery times whatever these are important factors, profitability might be a factor too that form their recommendations.

**[13:23] Other participant (system audio):** So it depends a bit on the situation.

**[13:25] Other participant (system audio):** But for e-commerce settings, I think they would really have some like retrieve augmented generation rack approach to limit the response to a certain subset or rank candidate.

**[13:38] Samarjit (mic):** So for these, like, third-party chat Bots that aren't using rag or these vector embeddings. How do they compare, like, products? Like, there might be, like, two shampoos that are both good for curly hair. How do they compare them?

**[13:54] Samarjit (mic):** You have thoughts on that?

**[13:55] Other participant (system audio):** I don't know. So.

**[13:57] Other participant (system audio):** This is a very specific example. So what I could imagine that you have maybe a pipeline or staged ranking procedure where you just get an initial set of candidates, all for curly hair, which match your query or your zoomed intent to your search intent.

**[14:13] Other participant (system audio):** And then the ranking logic could be based on the vector similarity.

**[14:16] Other participant (system audio):** To some specified preferences, but there could also be a lot of business rules like stock availability, profitability for the provider, which is, I think.

**[14:26] Other participant (system audio):** A very plausible choice. If you go to Amazon, they have amazon choice as a label, which clearly says it's their choice, not yours.

**[14:33] Other participant (system audio):** So I guess for the any commercial system, there's commercial interest encoded in some ways.

**[14:40] Other participant (system audio):** Or they took, they take like other information like reviews and average ratings as additional signals.

**[14:47] Other participant (system audio):** To.

**[14:48] Other participant (system audio):** Convince the buyer to convert to make a purchase.

**[14:50] Other participant (system audio):** So maybe it's not just profitability, but factored with the likelihood of purchase.

**[14:58] Samarjit (mic):** I see.

**[14:59] Samarjit (mic):** So.

**[15:00] Other participant (system audio):** And what else have changed? Maybe I can add this. I think what can change a lot is that there's a lot of research on transparency and explainability or justification of recommendations. Most literatures in that sense irrelevant because it's never put into practice. But now with llms, you can really generate some text at scale.

**[15:19] Samarjit (mic):** Yeah.

**[15:19] Other participant (system audio):** Like these are the pro points for a given thing that you want to persuade the customer to purchase.

**[15:24] Other participant (system audio):** So that changes a lot with llms.

**[15:26] Other participant (system audio):** I think.

**[15:29] Samarjit (mic):** So how do you think recommendation systems are going to evolve in the future? Like, what are the next evolutions you see in the horizon?

**[15:44] Other participant (system audio):** I mean my subjective hope in some way. So I work in academia and academia is obsessed with machine learning models and some abstract experiments and historical data sets, which are mostly useless. I think in reality because we don't need 1000 models. So my hope is, and this is my prediction is a biased wishful thinking is that the ranking part, like giving the user profile and the catalog is a commodity. We can take any of these models.

**[16:13] Other participant (system audio):** Like it seems for Amazon. So customers who bought this bought that, even if they do something different under the hood is good enough. So my hope is that the user interaction perspective will get more emphasis in the future because recommendation is a communication problem.

**[16:30] Other participant (system audio):** Like persuading people or making people confident in their choices is much more a lever that you can use than just okay surfaced some stuff here. And also this connects with discovery support, educating users while they're interacting. Understand if you say shampoo, I have no idea the recommender can help me understand the space of options I have.

**[16:53] Other participant (system audio):** So this is my wish for thinking for future research much more human interactive human oriented.

**[17:02] Other participant (system audio):** And that that's something llms are really good at. On the other hand, what I would hope for academic research is really much more impact oriented like real world deployments, real world metrics, real world studies about to understand what the real problems are, which I think are quite different from what we discuss in academia.

**[17:22] Samarjit (mic):** Okay, so you would like to see, like, more transparency, I guess, and, like, how the recommendation systems are making these recommendations for the, for the people.

**[17:31] Samarjit (mic):** Is that your home?

**[17:33] Other participant (system audio):** This is one aspect that could be more in the focus. I think the whole man machine interaction.

**[17:40] Other participant (system audio):** Aspect. So persuasion explanations is one part of it, but also how to ask people for the requirements, how much extra information to provide, how to guide users, how to understand, okay, this user is very fresh, has no idea of shampoo. So he's the expert who all knows everything already. They need different ways of communicating and.

**[18:02] Other participant (system audio):** Transporting information. So I think that's my hope that the field will develop and move away a bit from these, okay, there's some the millionth ranking model.

**[18:14] Samarjit (mic):** Yeah.

**[18:16] Samarjit (mic):** Do you have thoughts on whether these systems will eventually evolve such that they.

**[18:22] Samarjit (mic):** Complete the purchase for you? Like, if you, all you need to tell it is find me the best shampoo for me. And it researches all the shampoos. It finds one and just purchases it, purchases it autonomously, do you think?

**[18:37] Samarjit (mic):** That.

**[18:38] Other participant (system audio):** I think that's possible right now.

**[18:40] Other participant (system audio):** The question is if you have all these gigantic environments on your personal device, you can do this right now. I think that's not a problem technically.

**[18:49] Other participant (system audio):** The question is if you want it, if you trust that.

**[18:55] Other participant (system audio):** The system can make purchases on your behalf. And I'm quite sure that these systems would be effective. So if you just use these systems long enough that they know your preferences or proactively ask you if the agent turns out, okay, I don't know what you have to ask you some questions and then ask the user and then goes on the web and searches and makes recommendations or just says, okay, trust me, I will do it. I think that's very, very plausible. And I think.

**[19:21] Other participant (system audio):** Some tech savvy people just already do this.

**[19:23] Samarjit (mic):** Yeah. So for these agents, what do you think matters more? Context about the, the people or context about the product because, like, both are important, but which one comparatively matters more?

**[19:39] Other participant (system audio):** It's an interesting question. I think, yeah, as you say, you need to have both.

**[19:45] Other participant (system audio):** The question is a bit like.

**[19:49] Other participant (system audio):** Well, what's important for a customer?

**[19:52] Other participant (system audio):** So like if you, and that's why I repeat that this is a communication problem. If you have a sales expert, if you go to a store and they, the guy says, just take the product of brand X.

**[20:03] Other participant (system audio):** Because trust me.

**[20:05] Other participant (system audio):** So the information about the item is not too relevant, not even information about the consumer is relevant. It's just the trust into the system making or the recommend just being an expert.

**[20:17] Other participant (system audio):** So it could be even worse that you don't even need this match of.

**[20:21] Other participant (system audio):** References in a very detailed way, just establish a trust over time. That could be much more important for the long term acceptance. So if the consumer thinks, okay, that the choices are really good, I didn't think much. I don't want to think. And this may be also a dilemma we faced in our research. So we also started into explanations and user control. You can influence what the system should do. But then in the end, you think, I don't want this. I don't want to tell Netflix all the teachers. Just give me the good stuff.

**[20:51] Other participant (system audio):** And once you start trusting, it's good. Then I don't want these stuff anymore. I mean this interactive element.

**[20:51] Samarjit (mic):** Yeah.

**[20:59] Other participant (system audio):** So it's a bit even more than what you suggest.

**[21:02] Other participant (system audio):** Maybe.

**[21:04] Samarjit (mic):** I see.

**[21:08] Samarjit (mic):** And I guess, like, stepping back a little bit.

**[21:10] Samarjit (mic):** So what sorts of information about the person? What context about the person, like, matters the most? So, like, at a high level, this would look like what their tastes are, what their preferences are, but are there more specific things that.

**[21:25] Samarjit (mic):** Is very important for the recommendation system to know?

**[21:31] Other participant (system audio):** The individual user needs or preferences are. I think they remain central.

**[21:37] Other participant (system audio):** But again, then there's, it depends a lot on the use case.

**[21:40] Other participant (system audio):** If you have to, if you want to add additional information like we work a lot in the news domain. So what kind of content you consume in the morning and the weekends.

**[21:50] Other participant (system audio):** It is very different.

**[21:52] Other participant (system audio):** So this contextual information may play a role. Then depending on the domain, like in news, the recency is absolutely important. And after one day nothing is important anymore. So there are a lot of use cases specific types of information that you have. But I guess user and preferences are user tastes. They remain important. Now just thinking of the standard use cases of a media streaming YouTube social media.

**[22:19] Other participant (system audio):** So there's just a lot of work on other factors like personality traits of the user, which may be used. But our feeding is these are just secondary. They might help a bit, but in reality they're the fundamental topics.

**[22:33] Other participant (system audio):** I still most important.

**[22:36] Samarjit (mic):** I'm primarily. I'm primarily interested in, like, shopping agents. So, like. Like, recommendation systems for, like, products you can buy. So, like, would that. Is that the same?

**[22:47] Samarjit (mic):** In that. In that context?

**[22:54] Other participant (system audio):** Ly understand you, you do this, you want to understand if in the future we will have agents who do the e-commerce for you to go to the amazon, they purchase to make the transaction. That's what you're looking at in your program.

**[23:04] Samarjit (mic):** No. So what i'm asking is.

**[23:09] Samarjit (mic):** A zuma world, like a zoom that there will be these recommendation systems that will recommend products for you to buy, and they'll, like, buy those products for you as well. In that world, what sorts of.

**[23:23] Samarjit (mic):** Pieces of information do those systems need to have about the people for them to be as effective as possible?

**[23:34] Other participant (system audio):** Yeah. I mean like practically the operationalization would be either to ask them about.

**[23:42] Other participant (system audio):** Their immediate needs.

**[23:45] Other participant (system audio):** If they're like who initiates doing like if you want to purchase a TV set, it will not age, it will not proactively say it's time for something new might do so for a repeat purchase isn't consumable.

**[23:56] Other participant (system audio):** S.

**[23:57] Other participant (system audio):** But.

**[24:01] Other participant (system audio):** The needs, preferences and tastes of users remain important. So and then you can either ask which is nice for interactive chatbot like interactions. Plus I would also take, I think any agent would take the history of the individual user into account.

**[24:17] Other participant (system audio):** To see what the preference has been in the past, what has worked on the weekends.

**[24:21] Other participant (system audio):** Or what there the other could the question maybe is if such an agent, our such nation would leverage the collective behavior of others, which is a super helpful signal if you understand what the community patterns are. So if you think of an agent that runs locally on your machine or devices and on your behalf, that's the research and gets the items and makes a purchase.

**[24:44] Other participant (system audio):** So of course if the retrieval is based.

**[24:49] Other participant (system audio):** If it just goes to Amazon, let's say of course the system can learn that the consumer prefers.

**[24:55] Other participant (system audio):** Products that have like five star ratings or very high ratings or community averages.

**[25:03] Other participant (system audio):** But like this discovery feature that you have from this collective signal might be lost.

**[25:08] Other participant (system audio):** Unless the agent takes the user profile and transmits it to some other service and gets the recommendations from there.

**[25:16] Other participant (system audio):** The question could also be would this agent, let's assume in this case that you have an agent running on your device asks you for your preference and then goes to Amazon. Let's see. But then communicates with the recommender over there.

**[25:28] Other participant (system audio):** Not just retrieves the catalog and ranks, but rather says, okay, this is what my client wants. And then this system can leverage all the collective information there. So it depends on how this would be implemented.

**[25:33] Samarjit (mic):** Yeah.

**[25:42] Other participant (system audio):** I mean, one would be more privacy preserving.

**[25:45] Other participant (system audio):** Just running having a profile on your machine or it just sends everything to the provider.

**[25:51] Other participant (system audio):** Who knows.

**[25:52] Other participant (system audio):** This at the moment anyway.

**[25:58] Samarjit (mic):** So.

**[26:02] Samarjit (mic):** If, if both the people have a shopping agent and, like, retailers like amazon have their own shopping agent, the brands have their own shopping age on their website too. How do you think that. So you think those two shopping agents would negotiate with each other?

**[26:18] Samarjit (mic):** Or communicate with each with each other, representing both parties?

**[26:25] Other participant (system audio):** I find it difficult to imagine that they really like they impersonate agents in some ways and then talk to each other. So I think for now we would have maybe some API based solutions where you can do the shopping instructor some stuff and get back some information and decentral behind the API some logic.

**[26:45] Other participant (system audio):** That maybe contacts other sources of information. But I would not see like hackling agents somewhere over there.

**[26:54] Samarjit (mic):** Okay. Yeah, that makes sense.

**[26:54] Other participant (system audio):** Not now.

**[26:56] Samarjit (mic):** Yeah.

**[26:58] Samarjit (mic):** Yeah. So I know you said this wasn't your expertise, but I just wanted to get your thoughts on how advertising would work.

**[27:04] Samarjit (mic):** So if in the future, all of these shopping agents are buying products for us. They're not really looking at advertising in the traditional sense.

**[27:15] Samarjit (mic):** Because if, like, a robot looks at an advertising video, it's not going to have, like, the same, like, intuitive or emotional, like, pull towards that video. So, like, how do you think advertising will evolve as these agents start making purchases?

**[27:36] Other participant (system audio):** Interesting question because ads are designed for humans as they are now.

**[27:39] Samarjit (mic):** Yeah.

**[27:41] Other participant (system audio):** So how would you.

**[27:43] Other participant (system audio):** Of course you could have sponsored content would maybe be more important right now that in the background the ranking returned by the other side.

**[27:53] Other participant (system audio):** Or the content that is shown are made visible to the shopping agent.

**[27:57] Other participant (system audio):** Would be ranked based on payments.

**[28:00] Other participant (system audio):** Like if you have google search, you have the high ranked items there. Maybe that would be more.

**[28:06] Other participant (system audio):** Important than just these visual ads designed for humans if there's no humans.

**[28:11] Other participant (system audio):** But could it be that, I mean also it depends maybe on the.

**[28:16] Other participant (system audio):** Vision area we are with like what the future would look like if the shopping agent would maybe run on your computer like a chatbot and then it will harvest information from different sites.

**[28:28] Other participant (system audio):** And maybe also grab the ads and show them to you because I think the ads are good for you to discover something.

**[28:37] Other participant (system audio):** I don't know if there's.

**[28:39] Other participant (system audio):** That the ideas are forwarded somehow.

**[28:43] Other participant (system audio):** Due to the end user if they're still a user interface for the end user to the software agent. It's not just purchase me something.

**[28:51] Other participant (system audio):** But involve me in the dialog and ask questions and then decide the shopping agents go to the market and get the products and purchase system. If there's some interactivity.

**[29:01] Other participant (system audio):** Of the end user with the shopping agent and the UI then okay we can still have ads.

**[29:05] Other participant (system audio):** But I'm not sure this will be a future of how this works.

**[29:14] Other participant (system audio):** But as soon as you have an UI a UI for the end user, okay you can show the main recommendations and ask for confirmation for the purchase for example as soon as you have a screen. You can show ads again.

**[29:30] Samarjit (mic):** Yeah, that makes sense.

**[29:32] Other participant (system audio):** But yeah, but the traditional.

**[29:34] Other participant (system audio):** If it's just an API where I get the product enterprises and the transaction opportunity.

**[29:40] Other participant (system audio):** There's no point of having out.

**[29:43] Samarjit (mic):** Yeah.

**[29:46] Samarjit (mic):** Yeah. So, yeah, that. I think that covers all the questions I had.

**[29:50] Samarjit (mic):** But, yeah. Thank you.

**[29:52] Other participant (system audio):** Yeah. Can you share a few more words on what the project is you work on.

**[29:57] Samarjit (mic):** Yeah. So we're. We're trying to work on, like, a startup side project, so we're working the agentic commerce space. So right now what we're doing is we're just doing a lot of automations for e-commerce and dtc Brands. Part of what this involves is GEO or, like, enter engine optimization visibility services. You might have heard of the term GEO.

**[30:26] Other participant (system audio):** Yes.

**[30:27] Samarjit (mic):** Yeah. So that's what we're working on right now. But I am trying to think of ways to expand this idea into. Into advertising specifically, because I think that could be valuable, especially given that it's. I. My intuition is that advertising will change a lot given the chopping agents.

**[30:48] Samarjit (mic):** Are increasingly being used. And this will change how we serve ads to people.

**[30:54] Samarjit (mic):** So, yeah, just wanted to get your thoughts on it as someone who's been working in the field.

**[31:02] Other participant (system audio):** It's really very interesting. So I'm feeling personally I'm feeling way behind understanding what people actually already do.

**[31:10] Other participant (system audio):** Also.

**[31:12] Other participant (system audio):** Like also academic people who are not in computer science. They use agents to such an extent I'm intimidated. My students they use AI for everything.

**[31:14] Samarjit (mic):** Yeah.

**[31:21] Other participant (system audio):** In a very smart way by the way.

**[31:22] Samarjit (mic):** Yeah.

**[31:23] Other participant (system audio):** So I feel left behind already. So thanks for adding to this.

**[31:31] Samarjit (mic):** Yeah.

**[31:32] Samarjit (mic):** But, yeah, no, this was very helpful. Thank you for taking the time to talk to me.

**[31:36] Other participant (system audio):** Sure.

**[31:37] Other participant (system audio):** Again for the delay.

**[31:37] Samarjit (mic):** Yeah.

**[31:38] Samarjit (mic):** No worries.

**[31:38] Other participant (system audio):** But we made it.

**[31:39] Other participant (system audio):** Okay.

**[31:40] Samarjit (mic):** All right.

**[31:41] Other participant (system audio):** Wish you all the best. See you then.

**[31:41] Samarjit (mic):** All right. Thank you.

**[31:42] Samarjit (mic):** Bye.

**[31:43] Other participant (system audio):** Bye bye.
