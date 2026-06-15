# Stanford - AI Retail Tools

- Date: 2026-06-10
- Granola document id: 151a6e1c-404e-4c53-a8da-9ffd3a88302c
- Created at: 2026-06-10T15:58:58.655Z
- Attendees: Samarjit Deshmukh (samarjit.deshmukh.29@dartmouth.edu), Laura Fisher (laura.fisher@jdplc.com), shamitd@stanford.edu, Jetan Chowk (jetan.chowk@jdplc.com), Antonia Hansen (antonia.hansen@jdplc.com), armaan.priyadarshan.29@dartmouth.edu
- Content source: enhanced notes (AI summary panel)
- Transcript: verbatim from Granola, 130 segments

---

## Notes

### JD Sports: Company Scale and Context

- 5,500 stores globally, large enterprise retailer
- Jetan Chowk is CTO/CTO at JD Sports, Laura Fisher is EA to the Global CTO
- Jetan prefers “buy over build” but current enterprise solutions (Oracle, SAP etc.) cost ~£15M+ including SI and build costs
  - Opted to hire two data scientists/AI engineers to prototype internally first

### Key Pain Points (Jetan)

- Demand forecasting and replenishment
  - Replenishment currently based on sold items only, manually adjusted in Excel by merchandisers
  - Stock decrements come from three channels: in-store sales, ship-from-store, and click-and-collect
  - 8 to 10 day lead time from warehouse to store makes reactive replenishment too slow
  - Building internal predictive models on GCP to forecast forward-looking demand by market and country
- Online customer funnel underperforming vs. competitors
  - Missing fit finder and cross-brand sizing tool (sizes vary across Adidas, On Running, etc.), driving high returns
  - Wants style and trend recommendations tied to social/influencer signals, surfaced to employees and customers
- Also tracking: margin pressure, stock accuracy, assortment/outfit creation

### GEO and Answer Engine Optimization

- JD Sports already working with Profound for LLM discoverability
- Strategy: structured data on site, scaled media presence in key channels, cited in LLM responses not just Google

### Jetan’s Feedback on the Pitch Approach

- Hard to engage with problem discovery without seeing a concrete product first
  - “I have 50 problems in my business” so a defined value prop helps him triage
- Wants a demo before committing to further conversation
  - Will review a Loom and respond on whether it’s relevant
- Open to co-development if the product is credible and can be made enterprise-grade

### Next Steps

- Record and send Loom demo to Jetan (Samarjit)
- Jetan to review and respond by email on whether he wants to continue the conversation (Jetan, next week, in Athens for a global exec)

---

Chat with meeting transcript: [https://notes.granola.ai/t/010cc5d6-488a-40aa-a9ad-31b37a85b730](https://notes.granola.ai/t/010cc5d6-488a-40aa-a9ad-31b37a85b730)

---

## Verbatim transcript

**[00:00] Samarjit (mic):** Hi. How are you doing? Good. Thank you for taking the time.

**[00:08] Other participant (system audio):** No worries, no worries. Where are you based?

**[00:10] Samarjit (mic):** I'm in California right now. I go to school on the east coast.

**[00:18] Other participant (system audio):** Where in school is Stanford? Right?

**[00:20] Samarjit (mic):** No, that's my friend. I go to school at Dartmouth.

**[00:24] Other participant (system audio):** Okay, great. Waiting for this to join.

**[00:33] Samarjit (mic):** Yeah, I think we're waiting for Arm. On.

**[00:38] Other participant (system audio):** I just joined. Hi, how are you? Okay, thank you. How are you? Doing? Well? So it sounds like you reached out to a few of us on cold email. Which one of you is that? I think it was summerjit.

**[00:58] Samarjit (mic):** Yeah, I think it was me. Yeah.

**[01:01] Other participant (system audio):** Okay, great. Great. So we could say learn a little bit about yourselves and then see the tool that you developed.

**[01:07] Samarjit (mic):** Yeah. So, yeah, just as brief introductions, we're both Dartmouth students. We're both computer science majors. We're working on AI tooling for brands, small businesses and retailers. Essentially what we're working on right now is a store manager, an AI store manager that handles a brand or small businesses inventory operations, managing the storefront GEO, essentially the full stack. And we're still in the very early stages. So we're talking to everyone in the e-commerce industry to sort of understand what their problems are. What issues they're facing so we can develop a product further.

**[01:47] Other participant (system audio):** But. AI enabled product or is that something that. You built through application?

**[01:55] Samarjit (mic):** Yeah. It's definitely AI enabled. So it's an AI store manager, so.

**[02:03] Other participant (system audio):** I would say I still wanted to go. Okay, great. And when you say, because obviously we're quite a large retailer, we have five and a half thousand stores across the globe. So is it industrialized or enterprise driven cost kind of user?

**[02:23] Samarjit (mic):** Currently we're not working with brands or retailers at the scale of JD Sports. So the biggest brands that we're working with right now make a hundred million dollars in revenue. So right now at this stage, it's not big enough to handle the operations of larger, larger retailer.

**[02:42] Other participant (system audio):** Questions?

**[02:44] Samarjit (mic):** But we're in the process of trying to understand what problems larger retailers face so we can better, better help.

**[02:52] Other participant (system audio):** Can you show me it so I can see it comes better to life in my head if you can show me a live demo of it working?

**[02:59] Samarjit (mic):** Yeah, I don't have a demo in hand, but I can send over a loom video afterwards. That sort of showcases it.

**[03:10] Other participant (system audio):** I mean, look, I'm after more like a demo. In that in that sense and kind of after like I want to kind of see it working, it'd be great to see that if that's okay.

**[03:20] Samarjit (mic):** Yeah.

**[03:21] Other participant (system audio):** And physically see.

**[03:23] Samarjit (mic):** Yeah. I was thinking the way this call would be structured is sort of just understand, like, what problems you face rather than us, like, pitching you any particular product.

**[03:32] Other participant (system audio):** Me, it's like it's hard to conceptualize what you have. To then like, because I have, I have 50 problems in my business. Do you know what I mean? I also have replenishment problem. I have demand forecasting problem. I'm losing share online in my customer funnel online. I want to style and trends finder in my digital ecosystem and install with the employee to basically say, okay, you chosen this product. This is an outfit creation that can create basically assortment that I have based on what's on trending, what's on social, what's influencer led, etc. I have so many problems. I think to help you, you need to create what your value proposition is, what your product is. And that can help guide it through that. Avenue as opposed to what's the problems that you're facing because like transparently I have a margin problem. I have a stock accuracy problem. I have seven issues.

**[04:30] Samarjit (mic):** Ion of this is the most.

**[04:31] Other participant (system audio):** Do you see what I mean?

**[04:32] Samarjit (mic):** Yeah. Which one of those is the most pressing for you?

**[04:35] Other participant (system audio):** At the moment is a demand forecasting model. So at the moment we replenish, give me two seconds. Sorry. Yeah, like the issue. Okay, I'll give you one problem statement. I can't right now. So when I replenish a store, it's based on. Sold items in that store. Okay. Now the store has multiple avenues of how they decrement stock in that store. Customers coming into the store. Okay. And selling product on the shop floor. Fulfilling shit from store orders. Do you know what ship install orders are? Ordered online, but we use the store to fulfill it as the last mile. To the customer because it's quicker and faster. And then omnichannel orders, I click and collect. So they'll fulfill that install customer comes in, picks it up. Long story shortcast is built on sold items. So it's taking the sold items and then a merchandiser will manually go in and say it's saying. Five. It's hot right now. So let's make it seven. We'll just swim shorts hats instead of eight. It's all human done. Problem is how I think psychologically versus how you think as a merchandiser is completely different. So the ideals and the allocation is manually done. We then send that file through the warehouse management system then that picks it. It then gets shipped to the country because we've got one warehouse. It gets shipped to that country in a hub location. The hub breaks it down and then send it to the store. That lead time is eight to 10 days. And therefore. What happens is it's too late to replenish that stroke. So I need to move to a predictive forecasting model. Where I'm predicting what I think they're going to sell. In the next week as opposed to looking at sold items. And then I forward think that prediction and send that store stock that store earlier. Yeah. Have you guys like tried any like existing tools for this? Is it all just kind of manually? No, yeah. At the moment it's all menu done through excel, but we're building models internally to kind of automate and drive predictive analytics. But that's one big problem I'm facing right now. Right. The other piece is when you look at the customer funnel of my website where it's all the way from homepage all the way down to post checkout. It's reactively, it's just not upgraded to the standard that you expect to one of our competitors. There's a lot of products and features we need to develop. In addition to that, we're missing things like fit finder or sizing like because we're multi brand. I sell adidas and like coca on running et cetera. The sizes differ. What's a 42 in like might be slightly different for you in adidas. I don't know if you experienced that when you buy one brand. The size is something when you buy another brand, you may need to size up, size down. That drives a lot of returns. Which obviously is the cost of the business and therefore I'm trying to fix the sizing problem. So you could take any of those problems to me proposing a solution. To me problem. I'm keen in our kind of co-develop with you. So more on the inventory management side of things like what kind of models have you guys built so far and like has that kind of been better than manually doing it so far? We're still building it. It's on GCP at the moment. So we're building kind of with data scientists models which will take like for like cells, then put a bounce rate in there and then put things like what's trending, put weather, a whole bunch of data attributes and signals into the model to then predict what potentially a particular market in a particular country. Is going to be selling. We're still building that out. So I haven't specifically tested it yet. So I don't know where we are with whether it's going to work or not work. But like I say guys look for me to help you send me your send me a video. Then I can tell you whether it's of interest to me or not. Okay. Yeah, we can send out loom mic over. We didn't actually prepare a demo like for you specifically. Yeah. I mean for me I was more keen to see like recording recommendations engine I guess in your email to reduce. So send it send me a demo. I'll have a look at it. If I can help you I'll help you. Okay. Yeah. Also on that point how have you guys like been thinking about like answer engines? Have you been doing like GEO or kind of anything to optimize? Yeah, we focus heavily on kind of driving more discoverability on LLMs through reverse engineering sort of our position in geo and then AEO as well making sure that we drive to the answer as well. And really that's all around making sure we perfect. So we'll have more attributed structured data in our in our website. And then the second thing is also making sure we have media at scale in the right channels that make sure that when a customer asks within an LLM or prompt we're cited and just google. I see. Yeah and there's a tool called profound. You guys check them out there. Yeah. So we work closely with them. I see.

**[10:35] Samarjit (mic):** Yeah. Sorry. I just had one more question about the inventory management piece. So you said you're developing your own models in-house what made you choose that route over buying some third party software?

**[10:50] Other participant (system audio):** Good question. I hate to build. I like to buy. But at the moment if I go buy an application, I'm looking at 15 million pound. Take an oracle take an 09. Once you add in SI cost once you answer build cost once you add in the entire program in an enterprise business you're looking at in the millions. So before I spend the millions I rather spend a very small amount to hire two data scientists or AI engineers to kind of build my model first and see if I can solve for it myself. Doesn't make sense. Yeah but I'm more I'm more biases build. So if you guys miss the point I'm trying to make is I've got loads of problems. The problem is. You bring me something which is a credible product. I'll tell you if I'm interested or not. I'd rather start with the product. S that you already have as opposed to you trying to fix problems for me randomly. I rather you tell me what your proposition is. I'll tell you okay I like it but I need it enterprise grade ready. I need you to tweak it here and there etc. Then we could potentially talk. That makes sense. Does that make sense?

**[12:01] Samarjit (mic):** Yeah. Yeah. So we can send over a demo. We'll record a loom video for you. And you can review that. Would you. Be free to meet sometime next week to go over that?

**[12:16] Other participant (system audio):** Yeah, send me the demo next week I'm in Athens. In a global execut but I will email you back and let you know.

**[12:22] Samarjit (mic):** Okay.

**[12:23] Other participant (system audio):** What I'm interested. Okay.

**[12:24] Samarjit (mic):** All right. Sounds good.

**[12:25] Other participant (system audio):** Sounds good. All right. Thank you guys. Take care.

**[12:27] Samarjit (mic):** All right. Thank you for mute.

**[12:27] Other participant (system audio):** Thank you.
