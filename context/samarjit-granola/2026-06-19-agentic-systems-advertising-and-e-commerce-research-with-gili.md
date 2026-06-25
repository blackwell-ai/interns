# Agentic systems, advertising, and e-commerce research with Gili

- Date: 2026-06-19
- Granola document id: a54f16ba-7de8-4ca7-bee8-e6d414396047
- Created at: 2026-06-19T18:27:36.260Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 150 segments

---

## Notes

### About Gili Barali

- Researcher and professor, based in Rotterdam
- Work spans multi-armed bandits, reinforcement learning, and marketing/advertising optimization
- Focuses on individual-level data (vs. aggregate structural models)
- Sits on boards of several tech startups working on agentic systems

### Advertising and Individual-Level Modeling

- Early work: optimizing banner ads (e.g. on CNET, CNN) to drive store traffic and conversion
- Key technique: detect a user’s cognitive style in ~8 clicks
  - Cognitive style = how someone processes information (deliberative vs. impulsive, verbal vs. visual)
  - Once style is detected, serve the best-matching creative

- Shift from third-party data (retargeting) to first-party data due to privacy regulation (GDPR, Brazil’s LGPD)

### Agentic Commerce: What Gets Automated

- Key dimension is not high/low stakes, but pre-purchase uncertainty
  - Non-experiential products with clear, measurable attributes (e.g. laptops) are automatable
  - Experiential products (e.g. movies, consulting) have hard-to-know quality before purchase: stay human

- Predicted market outcome: “separate equilibrium”
  - Products either become premium/differentiated or get commoditized and fully agent-driven
  - Commoditized products compete on price/attributes; branding and storytelling lose value there
  - Branding and storytelling remain important for experiential, high-stakes purchases


### Reliable Agents in Regulated and High-Stakes Settings

- LLMs used for generalist/orchestration tasks only; not for accountable decisions
- For regulated decisions (clinical trials, loan applications, job ads): use formalized models
  - Multi-armed bandits, reinforcement learning with documented, auditable protocols
  - Logs kept; human review happens offline, not in real time

- Long-term concern: LLM training data quality is degrading
  - Incentives that drove content on Stack Overflow, Reddit, etc. are disappearing
  - Platforms tried lump-sum licensing deals (e.g. ~$1B contracts) but no durable solution yet
  - Some researchers working on attribution models to credit the 4-5 sources an LLM draws from

- For impact/effectiveness research: recommended Stefano Puntoni (Wharton) as the right reference

### Follow-Up

- **Look up Stefano Puntoni's research** (Samarjit)
  Studies where agentic/AI decision-making outperforms, matches, or underperforms human experts.
- **Email Gili with follow-up questions as the startup idea develops** (Samarjit)
  Gili offered to meet in person; travels to the US regularly for conferences and paper tours.

---

Chat with meeting transcript: [https://notes.granola.ai/t/0e96c8ea-eb9e-497c-af28-47d51bb4b3ec](https://notes.granola.ai/t/0e96c8ea-eb9e-497c-af28-47d51bb4b3ec)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** I must take a call now.

**[00:05] Samarjit (mic):** I want to ask him a lot of things.

**[00:12] Samarjit (mic):** Why a.

**[00:13] Samarjit (mic):** Castle?

**[00:14] Samarjit (mic):** We should.

**[00:18] Samarjit (mic):** Be like 600,000 pounds.

**[00:19] Samarjit (mic):** We are mine. You'll have to start the meeting, by the way.

**[00:46] Samarjit (mic):** Now.

**[01:44] Other participant (system audio):** Hello guys.

**[01:47] Samarjit (mic):** Hi. How are you doing?

**[01:49] Other participant (system audio):** I'm fine. How about you?

**[01:51] Samarjit (mic):** Ding gray.

**[01:56] Samarjit (mic):** Yeah. So just as a brief intro.

**[01:56] Other participant (system audio):** We also.

**[01:57] Other participant (system audio):** Have.

**[02:01] Samarjit (mic):** Yeah. So just as a brief introduction, my name is Samarjit.

**[02:05] Samarjit (mic):** I'm a student at Dartmouth College.

**[02:08] Samarjit (mic):** And along with Arman, we're working on. We're working the gentic commerce space. So agents buying and selling products.

**[02:17] Samarjit (mic):** So we're just doing a lot of research on everyone who works in the industry, and we just want to learn more, given that you've been working a lot in magetic systems, and I've seen that you've also written some Publications in marketing and advertising, which we're also interested in.

**[02:35] Other participant (system audio):** Nice to meet you. My name is Gili Barali. I'm happy to help in what I can.

**[02:40] Samarjit (mic):** All right, sounds good. So could you just to start off, could you tell me a little bit more about what you've sort of researched in terms, especially when it comes to advertising and how they relate to magentic systems?

**[02:55] Other participant (system audio):** Yeah. So.

**[02:57] Other participant (system audio):** My first work on that area was about using multi armed motor and bandits and reinforcement learning.

**[03:05] Other participant (system audio):** To solve advertising problems. I started with the display advertising.

**[03:09] Other participant (system audio):** And more recently we are moving towards using reinforcement learning and antientic systems.

**[03:19] Other participant (system audio):** Where I say the space is much more unclear because it's still evolving. There's a bunch of work that has been done to make llms more efficient.

**[03:28] Other participant (system audio):** But advertising itself, as you guys mentioned, is changing. So what should we optimize that's changing?

**[03:34] Other participant (system audio):** So far I was more focused on how to optimize developing mathematical algorithms that mathematical models that are implemented in algorithms and make basically solve optimization problems in marketing, especially in advertising.

**[03:48] Other participant (system audio):** Including website design, including which advertise the show at individual level.

**[03:53] Other participant (system audio):** But now it's more like, okay, what's the problem that we should be solving?

**[03:57] Other participant (system audio):** One thing that have been common across my work in the past and continues today is a work at the individual level data.

**[04:05] Other participant (system audio):** In modeling marketing, you have people who work with structural models where they look at aggregate data.

**[04:11] Other participant (system audio):** But assumptions and then estimate.

**[04:11] Samarjit (mic):** Yeah.

**[04:15] Other participant (system audio):** Consumer behavior based on assumptions in aggregate data. But I tend to focus on individual level data.

**[04:22] Samarjit (mic):** I see. So what's an example of this individual did? And also, when you, when you talk about advertising, this is what type of advertising is this? Is this as they're showing on websites or is it as they're run on, on TV? Like, what sort of advertising?

**[04:39] Other participant (system audio):** So my first work was on figuring out what is the optimal banner at the show to a person that visit the website. So it's captured in traffic to drive to the store. There are two parts, right? One was driving traffic, another one is given that you are at the store, what's the best way to make you convert?

**[04:56] Samarjit (mic):** Yeah.

**[04:56] Other participant (system audio):** In the capturing traffic? I used optimizing banners to get to, for example, banners on cinet.com and cnn to get people to go to a specific store.

**[05:06] Other participant (system audio):** And there the results exploration trade off where which is the best version.

**[05:13] Other participant (system audio):** For a person and later learning what is the best version in later profiting from it.

**[05:21] Other participant (system audio):** So basically that's the idea is that we have to learn enough information about individual, which was relatively easy before when you had, you could use third party data.

**[05:31] Other participant (system audio):** Like retargeting. But now it's basically first party data. So on your own website.

**[05:36] Other participant (system audio):** So given that information, how can you find the best, the optimal ad for yourself?

**[05:43] Other participant (system audio):** There is one part of it is learning about who is using the website and the other part is what is the optimal version of the website once the person is on the website. Where is the optimal version to increase conversion?

**[05:57] Other participant (system audio):** Yeah, so that's a bit on the technical side. What I mean by individual level data.

**[06:01] Samarjit (mic):** I see.

**[06:02] Samarjit (mic):** So how, how do you collect enough data to run these, like, reinforcement learning algorithms if it's only looking at one individual person?

**[06:12] Other participant (system audio):** So that's the thing. There's a richness of data. For example, in one paper we showed that we could figure out the cognitive style of the person using the website in eight clicks.

**[06:21] Other participant (system audio):** And cognitive style is how we process information. Some people are very deliberative before they make a decision. Some others are very impulsive.

**[06:27] Other participant (system audio):** Some people are verbal, some people visual and so on. So we develop tools that allow you to detect style of the person in about eight clicks. And then once you know enough about the person style, you can look at say, okay, what are the variations that I have, the creatives that I have and which one is the best for this style and then you serve it.

**[06:45] Samarjit (mic):** I see.

**[06:46] Samarjit (mic):** Have you done any research into.

**[06:50] Samarjit (mic):** Shopping agents? So, like, AI agents that buy products and navigate websites on your behalf.

**[06:58] Samarjit (mic):** Have you looked into that?

**[06:59] Other participant (system audio):** Yeah, so I'm looking to that, but not so much from a research point of view, more from an applied point of view. So I am on a board of a couple companies that they look at not what kind of algorithms, because the math is not going to be so much different. But what decisions should be given to agents and what decision should not be given to agents?

**[07:22] Other participant (system audio):** And that I think that's the next frontier. It's not so much, oh, is my llm better than yours? Do I do better or not? But it's a bit more like, wait a moment. Now we're talking about autonomy.

**[07:33] Other participant (system audio):** And what should allow, should we allow agents to buy as much as we want. What kind of guardrails are going to put, what kind of limits, what kind of structure we're going to put and what kind of decisions we're going to. But I've seen so many companies actually increase the amount of human work that is needed because they have the automate many decisions, but they want to keep what they call the human in the loop. And so they throw a lot of stuff for humans to review. And that's an issue as well. So that balance between what you automated and what you don't automate. And that's a tricky one. This is what I have been helping startups, tech startups with.

**[08:11] Samarjit (mic):** Yeah. So what are your thoughts on that? As I understand it, a lot of when people are buying things that are sort of needs or, like, low stakes, such as shampoo or paper towels or whatnot, you can automate that. But for a lot of purchases, people want to be in the buying process, especially for, like, more high stakes products. Is that sort of what you're seeing as well?

**[08:25] Other participant (system audio):** Yep.

**[08:36] Other participant (system audio):** You can't describe at the highest stake and low stake, but I think the most critical dimension is whether or not you can.

**[08:44] Other participant (system audio):** Before purchase.

**[08:46] Other participant (system audio):** Reduced uncertainty regarding what is the set of attributes and what is the quality along those sets. For example expatial products like movies is very hard to know what is the attribute, what are the key attributes in a movie experience that each person might be a different one. That's one. And second like for consulting services, it's hard to know the quality of the service before it's actually provided. You might know the dimensions, but the actual quality you only know after the purchase or during consumption. So I think what's going to happen is that the agents will automate things that are a non experiential, have a very clear set of attributes and you can rate very, you can say clearly what is the level of each attribute on each product.

**[09:31] Other participant (system audio):** Parse. Well, cars is a very difficult one. Let's take a laptop. So I want to replace my MacBook. I can't just get an agent for that because I have a very clear set of attributes and I and we can say this MacBook has that size of screen that a bunch of memory. So there is no uncertainty over there.

**[09:37] Samarjit (mic):** Yeah.

**[09:47] Samarjit (mic):** Yeah. That makes.

**[09:50] Samarjit (mic):** That makes sense.

**[09:50] Samarjit (mic):** So.

**[09:52] Other participant (system audio):** For Saritan to robot for marketing. It has a big implication, which is it reduces the value of storytelling.

**[10:00] Other participant (system audio):** Which was a big trend some time ago and reduces the value of branding.

**[10:05] Other participant (system audio):** For those products. It increases the value of those things, storytelling and branding for the exponential products, for the things that you have to have the human in the loop.

**[10:15] Other participant (system audio):** Because they become it still is an emotion process or high stakes settings. And their branding is still there. Storytelling is still there. People are still in the loop.

**[10:25] Other participant (system audio):** But the other ones, I think they'll be most automated.

**[10:29] Samarjit (mic):** Yeah, actually, yeah, I wanted to ask about that. So for these.

**[10:34] Samarjit (mic):** For these products where it's, where it's very easy to tell, measure their quality based on attributes, how do you, how will companies be able to differentiate themselves? For example, if there's, like, 10 different soap manufacturers and they all have, like, similar levels of soap right now, they compete on branding in the future. How will they sort of differentiate?

**[10:56] Other participant (system audio):** Yeah, I think their marketing is going to be more important because if they can have something special, if there is no one dimension that cannot be automated, if they are, they cannot differentiate themselves, they will be commoditized. And in that case, they will be, the agents will dominate.

**[11:20] Other participant (system audio):** So it could be that in over time we're going to see a situation where products either become.

**[11:26] Other participant (system audio):** More premium and has something special. They have something special or they are going standardized and then agents will be doing the buy.

**[11:38] Samarjit (mic):** Yeah. Yeah. That sort of.

**[11:39] Other participant (system audio):** Separate equilibrium.

**[11:40] Samarjit (mic):** Yeah, that's sort of what my, my thoughts on that were, too. Also, I saw that you have a lot of research on agentic decision making based on low information environments.

**[11:53] Samarjit (mic):** So could you tell me a bit more about that? What sorts of environments were you looking at specifically?

**[12:00] Other participant (system audio):** What paper are you referring to?

**[12:02] Samarjit (mic):** Yeah. Let me pull it up.

**[12:10] Samarjit (mic):** Yeah, I think, like, on your website, you say you develop AI methods for adaptive decision making under uncertainty in, like, high states and regulated settings.

**[12:20] Samarjit (mic):** So.

**[12:20] Samarjit (mic):** Yeah.

**[12:21] Other participant (system audio):** Yeah. So I got, for example.

**[12:25] Other participant (system audio):** Clinical trial setting where you're trying to figure out what the medication you're going to give to another patient entering a trial. So one of my papers is being used now by a company to develop a service where they help clinical trial companies like big pharma companies.

**[12:40] Other participant (system audio):** To decide how to run their trial. So it's highly regulated. You have to be very sure that what you're doing is following a protocol. So this is the kind of stuff that I mean by a regulated.

**[12:52] Other participant (system audio):** And having little information is because now we have less and less information from the individual, especially because of third party barriers like gpt and sorry.

**[13:04] Other participant (system audio):** Grp.

**[13:06] Other participant (system audio):** I forgot the regulation in the European Union.

**[13:10] Other participant (system audio):** And also in Brazil they have regulation protecting private taking care of privacy and data protection.

**[13:19] Other participant (system audio):** Yeah, I think that's a big part of it.

**[13:22] Samarjit (mic):** So how do you ensure that the agents or the lms, like, produce, like, accurate output and these, like, high stakes decisions? Because, like, every mistake is, like, very, like, costly, right? So, like, how do you ensure they're, like, almost, like, basically perfect?

**[13:35] Samarjit (mic):** In.

**[13:36] Samarjit (mic):** Their.

**[13:37] Other participant (system audio):** Yeah, well, there is a short term also in the long term. So I'll start with the long term. Then we can go to the short. On the long term, things are problematic.

**[13:45] Other participant (system audio):** Because lms were developed based on a world where there were a set of incentives for people to produce content. For example, stack overflow, reddit and so on.

**[13:55] Other participant (system audio):** And they learn from that.

**[13:58] Other participant (system audio):** But the incentives that made those people to be there and right there, write that are not there anymore. Oftentimes people get the results from chat GPT and it does not as explicitly gives credit where they got information from. So that means also you can even see that some people at the stack overflow were pushing back and trying to give wrong answers just because they know that there is an agreement, a licensing agreement between the platform and open air. So the incentives that were there to produce content that is used by llms.

**[14:33] Other participant (system audio):** Are not there anymore. They are still figuring out what are going to be the new incentives. They tried some lump sum incentives like $1 billion contract with, I think it was added or stackable. So they tried that, but I don't think they have found that yet.

**[14:49] Other participant (system audio):** So on the long run, this is a problem because I don't know if agents will be doing a good job as much as they are now because the data they are trained on will disappear or at least will not be as robust as it's now.

**[15:04] Other participant (system audio):** There is work being done that on the legal side for licensing models, but that's still something that's being tried. Some I've been helping some researchers with their papers on.

**[15:15] Other participant (system audio):** How do they give a distribution problem? How do they give credit to four or five sources that llm got information from? So they're trying to do that bit like that saying here is the result from chat GPT and here are the four sources that I used so that they're experimenting there.

**[15:34] Other participant (system audio):** As for the short term, I think the answer is.

**[15:40] Other participant (system audio):** I don't think agents will be used for this kind of situations.

**[15:47] Other participant (system audio):** What I have been doing is for highly regulated settings.

**[15:52] Other participant (system audio):** We use agents for generalist tasks context. But when it comes to actually doing the technical decision, which you have to be accounted for and which you have to be explained and where they came from, then you use a very tight or type of model operations research type of model, multi-banded and reinforcement learning where you control the parameters and kind of explain another one explain. You can document beforehand exactly what is the process that you're going to be using to make those decisions.

**[16:24] Samarjit (mic):** See. And so this research is primarily, like, a clinical setting, or are there other sort of environments you looked at?

**[16:30] Other participant (system audio):** No, Sam, that's a general model. Even though we tested in clinical settings, the non clinical settings are also applied because, for example, think about finance. You have to loan applications, you have to provide that kind of highly regulated setting. Think about advertising job offers, right on linkedin and other sources. So it's a general problem that we use one of these data sources.

**[16:58] Samarjit (mic):** Yeah. So if I understand correctly, so the way you ensure it doesn't make any mistakes is you have it be grounded in specific data sources.

**[17:07] Other participant (system audio):** And grounded on very explicit formalized models.

**[17:11] Other participant (system audio):** That you can document and they are not.

**[17:14] Other participant (system audio):** So think about the agent as a manager that organized and orchestrate things. But at some point the manager says, okay, now I have to make a decision and I have to be accountable for that decision. So I'm going to call this specific, let's call procedure or function. That is leaves a log, a very clear log and has a protocol defined decision process. It could be just a maximization problem using traditional operations research methods.

**[17:42] Other participant (system audio):** Such as bandits, for example.

**[17:46] Samarjit (mic):** And then there would be a human like who's reviewing those logs to ensure nothing.

**[17:50] Other participant (system audio):** You have to prepare for that. Yes. In a clinical trial, you don't have to have a human in real time reviewing those decisions. But like you said, the logs, yes.

**[18:02] Samarjit (mic):** I see.

**[18:03] Other participant (system audio):** So yeah, yeah, offline.

**[18:06] Samarjit (mic):** In your research, did you find how effective these agents were at, like, managing or, like, making these decisions?

**[18:14] Samarjit (mic):** Like, compared to, like, a normal to compared to a regular human or an expert in the field? Did the decision, were they making better decisions? What are their decisions worse? Were they equal?

**[18:27] Other participant (system audio):** For this kind of evaluation, I would suggest research by Stefano puntoni, a friend of mine who used to be at the rasmus now is at work. He's looking at the impact. I tend to develop algorithms and he's more focused on the impact side.

**[18:42] Other participant (system audio):** He's been looking at studies that actually measure and check those things.

**[18:47] Other participant (system audio):** He is better able to say what kind of settings it works better, what kind of settings do not work.

**[18:53] Samarjit (mic):** Okay, yeah, I'll take a look at that.

**[18:58] Other participant (system audio):** So what's the context? Is this a term paper or are you thinking about a startup or a research project?

**[19:05] Samarjit (mic):** Yeah. So, yeah, we're thinking of building a startup in, like, e-commerce or, like, a jet to commerce. So we're just talking to a lot of people who might be more informed than us on sort of where the industry is heading, how agents are evolving just to learn more.

**[19:23] Other participant (system audio):** And is it in stealth mode or can you talk a little bit about the goal of the startup or how it's positioning itself?

**[19:30] Samarjit (mic):** Yeah. Sort of in stealth mode. We're still in the early stages, so we're trying to refine the idea.

**[19:35] Other participant (system audio):** Okay.

**[19:35] Other participant (system audio):** Okay.

**[19:36] Other participant (system audio):** And you're all in computer science backgrounds or diverse.

**[19:40] Samarjit (mic):** We're all in the wrong computer science.

**[19:40] Other participant (system audio):** Or?

**[19:46] Samarjit (mic):** But, yeah, I think that's all the questions I had. But, yeah, thank you for taking the time to talk with us today. This was very useful.

**[19:53] Other participant (system audio):** Good. I'm happy to help. And if in the future you have more questions or you want to have a regular chat and I'm oftentimes into us actually came back three days ago, we can always sit down and talk.

**[20:04] Samarjit (mic):** Yeah, we're in.

**[20:04] Other participant (system audio):** Have a good friends in all these places.

**[20:06] Samarjit (mic):** The us. Are you, are you based?

**[20:09] Other participant (system audio):** So I'm not based in the us. I'm based in Rotterdam, but I was in the doctoral consortium.

**[20:14] Other participant (system audio):** In New York.

**[20:15] Samarjit (mic):** I see.

**[20:16] Other participant (system audio):** Every year we pick up the doctoral students and we select some faculty and we invite them over to guide this doctoral students in terms of research and kind of stuff that they can do.

**[20:29] Other participant (system audio):** And this year was in New York at Fordham. Next year is going to be in the Netherlands a couple years ago. So every year it varies.

**[20:40] Other participant (system audio):** But every year I go to the US for something or another conference presenting papers. I'm just finishing up two papers that I probably going to do a tour to present to get some input before we send to a journal. So I should be around.

**[20:55] Samarjit (mic):** Okay. Yeah. If I have any questions come up, I'll shoot over an email. Thank you for talking with us.

**[21:01] Other participant (system audio):** Yep. Good luck and all the best for you guys.

**[21:03] Samarjit (mic):** All right, bye.
