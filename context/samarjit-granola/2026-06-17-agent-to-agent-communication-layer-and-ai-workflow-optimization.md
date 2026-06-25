# Agent-to-agent communication layer and AI workflow optimization

- Date: 2026-06-17
- Granola document id: d105a0f7-e625-48b4-af52-88dc7e7cb05e
- Created at: 2026-06-17T23:30:17.338Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu)
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 146 segments

---

## Notes

### Their Company and Context

- Building an agent-to-agent communication and coordination layer
- Running 15-20 agents simultaneously internally, across multiple machines
- Vision: agents with specialized context message each other directly (e.g. CTO agent pings desktop app agent for a spec review)
- Each agent has a unique ID and directory address, like an email equivalent
- Messages enter the target session live, no intermediary needed

### Their Tech Stack

- Primarily Claude Code (90%)
- Codex for image generation and content (blog posts, social media)
- Open Claude for LinkedIn automation scripts, but usage has dropped significantly
  - Noted that a payment network contact said Open Claude traffic dropped by half recently
  - Now mostly kept because it was already set up, not because it’s better

- Railway, Vercel, Supabase for hosting

### Workflow and Agent Architecture

- Isolated tasks, each pointed to one main agent that spawns sub-agents
  - Sub-agents share context within the session, no cross-task communication needed

- Moved away from Cursor and Superset; now almost entirely Claude Code
  - Cursor previously used for drafting plans; now rarely opened
  - Tried RL loops (Ralph Wiggum) briefly

- Increasingly hands-off: Claude generates plans, reviews its own code, handles execution

### Fit for Their Product

- Current setup (isolated tasks, shared sub-agent context) doesn’t create an obvious need for agent-to-agent messaging
- But: actively building out an internal “company brain” with specialized agents across outbound, research, and other functions
  - Only started a few days ago, want to make it more useful
  - This is exactly the use case their product targets

- Interested in trying an MVP, specifically the desktop messaging layer they carved off

### Next Steps

- Send over MVP / working demo of the agent-to-agent desktop messaging app (them, next week or the week after)
- Likely meeting in person next week

---

Chat with meeting transcript: [https://notes.granola.ai/t/eea759b3-7358-4e41-abd7-0f9a3c10dc75](https://notes.granola.ai/t/eea759b3-7358-4e41-abd7-0f9a3c10dc75)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** What.

**[00:01] Samarjit (mic):** Hi, how are you doing?

**[00:03] Samarjit (mic):** Good. How's it going? Going good.

**[00:06] Samarjit (mic):** Nice man. Nice to meet you.

**[00:09] Samarjit (mic):** Yeah, no worries.

**[00:11] Samarjit (mic):** So you just finished up your first year at Dartmouth. Is that right? Yeah, that's correct.

**[00:18] Samarjit (mic):** How was it?

**[00:20] Samarjit (mic):** It was great. It was great. I learned a lot.

**[00:23] Samarjit (mic):** Very great socially.

**[00:25] Samarjit (mic):** Yeah, it was fun.

**[00:27] Samarjit (mic):** Cool.

**[00:28] Samarjit (mic):** Very nice. And so you guys are working on something new. I couldn't find much about the company.

**[00:35] Samarjit (mic):** Yeah. So what do you guys work on?

**[00:38] Samarjit (mic):** Yeah, so we're essentially working on the e-commerce space. So we're trying to create AI agents that can run brands autonomously.

**[00:43] Other participant (system audio):** Cool.

**[00:49] Samarjit (mic):** So there's a variety of like DTC brands that we've been working with and we've sort of realized that a lot of the operations in the day-to-day can be handled.

**[00:59] Samarjit (mic):** With AI systems. So yeah, sort of just like running brands ourselves.

**[01:05] Samarjit (mic):** And helping other brands manage their operations.

**[01:10] Other participant (system audio):** Love it.

**[01:10] Other participant (system audio):** It's going to be a big space. It'll be a good space.

**[01:13] Samarjit (mic):** Yeah.

**[01:15] Other participant (system audio):** Well, thanks for taking the time. Looking forward to.

**[01:18] Other participant (system audio):** Probably meeting you next week in person.

**[01:22] Other participant (system audio):** A little bit of context. So we are working on.

**[01:26] Other participant (system audio):** Agent to agent communication layer.

**[01:30] Other participant (system audio):** And vibration layer and talking to a lot of different trying to talk to different folks working on different things to understand really the main thing is just understand how they're using AI, what they're using to build.

**[01:42] Other participant (system audio):** Today. And then kind of what their workflow looks like. So codecs, quadcode, how many session windows you've opened typically, how you and your co-founders kind of coordinate work between yourselves and your agents. That's like the gist. So should be pretty quick, just like 10, 15 minutes. But really, we just love.

**[02:01] Samarjit (mic):** I'm a little.

**[02:01] Samarjit (mic):** Bit.

**[02:03] Other participant (system audio):** Go ahead.

**[02:03] Samarjit (mic):** Yeah, so when you say agent to agent communication layer, what is that? What does that mean exactly?

**[02:08] Other participant (system audio):** Yeah. So like we run like 15 to 20 agents at a time.

**[02:13] Samarjit (mic):** Yeah.

**[02:14] Other participant (system audio):** And internally internally. And some of them we need to.

**[02:19] Other participant (system audio):** We just want them to work, right? Them to work as a team, them to collaborate.

**[02:24] Other participant (system audio):** If one of them needs something from another event, it can message the other agent directly.

**[02:28] Other participant (system audio):** It can be on a different machine.

**[02:31] Other participant (system audio):** Like my quad code agent after it finishes something before it submits the PR, it can message my codex agent on a different computer to do a code review that codexation does a code review. It reports back to the agent hypothetically, right? Or if we're doing like social content.

**[02:48] Other participant (system audio):** I might have like three or four different agents that all work together.

**[02:51] Other participant (system audio):** Across a couple different computers.

**[02:54] Other participant (system audio):** And they need a way to just quickly communicate directly.

**[02:59] Other participant (system audio):** So that's like the short, that's like the gist.

**[03:03] Other participant (system audio):** Yeah.

**[03:04] Other participant (system audio):** But we're trying to get a sense for like how other people are working because trying to figure out.

**[03:09] Other participant (system audio):** Whether people need something like that.

**[03:12] Other participant (system audio):** And who are the types of people that might need something like that versus don't.

**[03:16] Other participant (system audio):** Like builders may not need it. Marketing teams may hypothetically.

**[03:22] Samarjit (mic):** Yeah, my thoughts on that are sort of, if you have a predefined task, like a concrete task, what the way that our workflow works is that we have one agent that's responsible for handling that task. And that agent spawns a lot of sub agents, but all of those sub-agents are working under the main agent. They all have shared contacts, right? So I don't see the need for them to have some sort of way to communicate because it's already built into cloud code. So yeah, we have.

**[03:57] Samarjit (mic):** The way we work right now is we sort of have a bunch of isolated tasks.

**[04:01] Samarjit (mic):** That we each point an individual agent to. So there's no need to share context between tasks.

**[04:08] Samarjit (mic):** If that makes sense.

**[04:10] Other participant (system audio):** Yeah, makes sense. So you guys have split the work where you might have an isolated task.

**[04:15] Other participant (system audio):** It doesn't need collaboration with maybe some of the other agents that might be working on other tasks. And then a club code session just spins up sub agents to do any work that it might need. And obviously that stage is within that isolated task.

**[04:21] Samarjit (mic):** Yeah.

**[04:27] Other participant (system audio):** Is that right? Is that a summarize that right?

**[04:29] Samarjit (mic):** Yeah.

**[04:29] Other participant (system audio):** Cool. Uh, so you guys using quad code.

**[04:34] Other participant (system audio):** And what other tools kind of are in your tech stack?

**[04:38] Samarjit (mic):** We used to use this ID or we used to use this thing called superset for orchestration. You might have heard of it, but primarily we've just been relying on like clawed code.

**[04:51] Samarjit (mic):** There are certain.

**[04:53] Samarjit (mic):** Modifications we made. Like for example like Ralph Wiggum loops. We've tried that out a little bit. I also use cursor sometimes in conjunction with cloud code. But yeah, that's where tech stack looks like right now.

**[05:08] Other participant (system audio):** When you use, when you choose to use cursor versus quad code? Is there any like pattern of when you choose to use that?

**[05:16] Samarjit (mic):** Yeah, I've started using cursor less now, but originally I used to use cursor for drafting up plans.

**[05:24] Samarjit (mic):** I could understand. I started to become like much more hands off now in the sense that before I used to dive into the code base a little bit more. Nowadays I sort of just sometimes I don't even look at the code. I just like tell like claw to generate a bunch of plans and then tell it to like review the code itself. So.

**[05:45] Samarjit (mic):** And claw just handles everything.

**[05:47] Samarjit (mic):** But yeah that's sort of how we've been working.

**[05:51] Other participant (system audio):** Makes sense.

**[05:53] Other participant (system audio):** And then have you used codex at all?

**[05:55] Samarjit (mic):** I use codecs like a long time ago so maybe like maybe back in like 2025 I haven't used it recently.

**[06:03] Other participant (system audio):** Okay.

**[06:03] Samarjit (mic):** So I don't know how its capabilities are.

**[06:06] Other participant (system audio):** So you guys are all in on cloud code now.

**[06:08] Samarjit (mic):** Yeah.

**[06:09] Other participant (system audio):** I love it.

**[06:10] Other participant (system audio):** Same. Yeah, we're like 90% club code.

**[06:14] Samarjit (mic):** What's your guys'tech leg? What do you guys use for to be as productive as possible?

**[06:19] Other participant (system audio):** Yeah. So.

**[06:22] Other participant (system audio):** Quad code primarily, we use codecs a little bit.

**[06:26] Other participant (system audio):** Mainly if like one agent needs an image generated.

**[06:31] Other participant (system audio):** Or like content like a blog post social media content, whatever.

**[06:34] Other participant (system audio):** It'll message a cloud codex agent to generate some options and then return those because codecs is better because quad code doesn't have an image generation model.

**[06:43] Samarjit (mic):** Yeah.

**[06:44] Other participant (system audio):** Of open claw for like some random like sketchy stuff like LinkedIn automation and stuff like that that cloud code may not be as good app.

**[06:54] Other participant (system audio):** We've built the obviously the internal stuff for agent to agent communication and collaboration. So that's all where everything runs.

**[07:00] Other participant (system audio):** And then everything's just hosted on, you know, the usual stuff railway Vercel.

**[07:06] Other participant (system audio):** Super base.

**[07:06] Samarjit (mic):** A couple yeah couple of questions so I've tried to open cloud as well I found that the latency for open claw is like really really bad like it's very slow in terms of like complete tasks and I found that cloud code can like handle a lot of a lot of these tasks on its own so for example linkedin outreach I feel like cloud code can handle that better using like play ride or like other browser automations we use cloud code a lot for emails as well so what's your open class setup? How have you made that optimized?

**[07:08] Other participant (system audio):** Yeah.

**[07:37] Other participant (system audio):** I use it a lot less.

**[07:39] Other participant (system audio):** Now.

**[07:39] Samarjit (mic):** Okay.

**[07:39] Other participant (system audio):** Originally I was back when I in February, January, maybe late Jan when I first started using it.

**[07:46] Other participant (system audio):** I was doing a lot with it.

**[07:48] Other participant (system audio):** And cause quad code was fine, but it was still missing some things.

**[07:52] Other participant (system audio):** But I think the open plot hype caused anthropic to add a lot of features to quant code.

**[07:59] Other participant (system audio):** That didn't previously exist. And so now most of my 90%

**[08:03] Other participant (system audio):** Is on quad code. I just had my LinkedIn.

**[08:08] Other participant (system audio):** Kind of scripts and jobs running originally on open claw and I decided I just don't want to move those over to club code, but everything else I've basically moved over to club code at this point.

**[08:20] Other participant (system audio):** Yeah, it's and I think I was chatting with somebody yesterday that a lot of they like an agent payment network essentially and a lot of their traffic comes from cloud open flaw agents and they said it's dropped in half in recent times. So I think open clause being used a lot less.

**[08:38] Samarjit (mic):** I see.

**[08:40] Other participant (system audio):** Yeah.

**[08:41] Other participant (system audio):** So I don't, I don't think you really need open flaw anymore. Like the only reason I have it is just because I it was already there.

**[08:48] Samarjit (mic):** Yeah and so the way your agent to agent communication layer would work is is that like a sort of like a slack for agents or like how.

**[08:59] Other participant (system audio):** S just direct, direct message. It goes directly into the session.

**[09:02] Samarjit (mic):** Okay.

**[09:03] Other participant (system audio):** So no like no need for like an intermediary type of slack type of thing. It's like each agent has an agent ID and essentially an equivalent of an email address. It's not an email address, but it's an equivalent of an email address.

**[09:16] Other participant (system audio):** There's a directory. So in agent and if it knows it needs to message another agent, it can look up.

**[09:23] Other participant (system audio):** All the agents and the directory on that in our company. It can see their address just like you would a human, right? Like you can look up other humans in a directory get their email address and send them an email. Same thing here.

**[09:35] Other participant (system audio):** And then they just send the message and it enters the session live.

**[09:39] Samarjit (mic):** So what's your vision for a task that this could be useful for?

**[09:45] Other participant (system audio):** Happy.

**[09:45] Samarjit (mic):** Well.

**[09:47] Samarjit (mic):** For us at least.

**[09:50] Samarjit (mic):** We we run the entire company on search cells.

**[09:56] Samarjit (mic):** And like 40 different agents yeah probably half of them are like coding agents but like I don't I got in different coding sessions and agents that I've kind of made a specialized agent like certain ones that are code review agents for agents that are specialized on the API or the mcp or whatever the SDK or the desktop app.

**[10:21] Other participant (system audio):** And those agents because they have specialized context on a certain part of something needs to be added to the desktop app. My CTO agent knows, okay message the desktop app agent.

**[10:32] Other participant (system audio):** That desktop app agent then can ask three other kind of other agents to provide input on the spec. I mean, you can do this with some with sub agents to some degree.

**[10:43] Other participant (system audio):** But sub agents share the same context and I keep them separate because I want them to have specialized context.

**[10:48] Samarjit (mic):** Yeah so one thing so one thing we've been doing is we've tried to like create like a company brand for our own company so we have sort of like a similar setup to what you're describing where we have like outbound outreach agents then we have researcher agents that like pull up like papers or like exposts or whatever we have a bunch of so we have like agents like sort of handling every aspect of our like business and we've this is something we've only been like working on for like the last couple of days but I want to make this better and like more more useful for us so if you have like like an MVP of your of your like a product we would be willing to use it and try it out and give you feedback on that.

**[10:56] Other participant (system audio):** Yeah.

**[10:56] Other participant (system audio):** Nice.

**[11:34] Other participant (system audio):** Yeah, we I the product has a couple different layers but I carved off just the desktop messaging.

**[11:41] Other participant (system audio):** Application to it to allow if somebody wants to use just the agent to agent messaging. They can use that.

**[11:49] Other participant (system audio):** I could get it. I could probably give it to you next week or the following week whenever. But it's cool because.

**[11:53] Samarjit (mic):** Okay.

**[11:56] Other participant (system audio):** You can have if you leave especially if you leave the sessions open.

**[12:01] Other participant (system audio):** They can all work together. So like mine run on loops, right? So like every day 3 a.m.

**[12:09] Other participant (system audio):** My CTO agent knows to go check in on all the engineering agents, remind them to update things. Ask if they have any things that they need from from me for example. And then in the morning I can see, okay, like I just talked to my CTO agent. He's like, hey.

**[12:26] Other participant (system audio):** Whatever the back end engineer had, you know needs these things.

**[12:31] Other participant (system audio):** And then I can unblock it.

**[12:33] Samarjit (mic):** Yeah that's sort of what I'm trying what I'm envisioning are like internal company brain would look like as well autonomous loops that work while we're away or sleeping or whatever but yeah if you could send over like a MVP or like a working demo I definitely give it a look.

**[12:34] Other participant (system audio):** But.

**[12:45] Other participant (system audio):** Yeah.

**[12:53] Other participant (system audio):** I can do that probably next week.

**[12:54] Samarjit (mic):** Alright.

**[12:55] Other participant (system audio):** Let me set a, I'll set a reminder to do so.

**[12:58] Other participant (system audio):** In case you guys want to try it out.

**[13:02] Other participant (system audio):** Sweet man.

**[13:05] Other participant (system audio):** Anything else I can help with?

**[13:07] Other participant (system audio):** Or.

**[13:07] Other participant (system audio):** If if I can help with anything along the way.

**[13:10] Other participant (system audio):** To summon up.

**[13:11] Samarjit (mic):** Yeah if anything comes up I'll definitely send over a DM on slack.

**[13:18] Samarjit (mic):** Thanks for meeting with.

**[13:18] Other participant (system audio):** Okay.

**[13:19] Other participant (system audio):** Appreciate it. See you next week. Thank you. See ya. Bye.
