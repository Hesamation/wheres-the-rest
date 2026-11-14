# Where’s the Rest? — Video production brief

Prepared November 13, revised November 14, 2026. Local GLM production handoff prepared November 14. Supplied narration is ready at `assets/narration.wav` (102.28 seconds; PCM signed 16-bit, 24 kHz, mono). Footage and edit have not been produced. Read `START-HERE.md` first; its supplied-audio workflow supersedes the optional voice-generation instructions below.

## Goal and direction

Create an approximately 100-second narrated hackathon demo; acceptable range 90–115 seconds, maximum 120 seconds. English, no facecam, zero additional spending.

**The finished video has narration throughout. The 10–15 second voice audition below is optional preparation, not the final soundtrack. Generate the entire spoken script for the finished film, with brief deliberate pauses for the reveal and evidence inspection.**

Story: successful payout → incomplete QA payout → “Where’s the rest?” → cross-chain explorers already exist → check the same source hash in both explorers → the payout question remains → reconcile the evidence → report handoff → current scope and future direction.

Confident, curious, slightly dry delivery. Match the app’s charcoal background, blue accents and precise typography. Use real product footage, close-ups, large numerical annotations and deliberate cuts. The central reveal is: “Three identical burns. Same recipient. One observed transfer.” Brief silence. “Where’s the rest?”

Identify the discrepancy as a **public staging QA test on mainnet**. It is not a demonstrated production customer-loss incident. Missing records do not establish permanent loss or root cause. Label future features as future directions.

### Positioning for a technical viewer

**Cross-chain explorers and reconciliation products already exist.** After the reveal, briefly show the same QA1 source-hash search in NEAR Intents Explorer and Range. Then return to the payout question: do all three executed withdrawals have matching evidence? The comparison is a manual investigation step in the video. The application itself queries NEAR RPC, Chaindefuser and Base RPC; it does not query those explorers.

**Explain what the available evidence leaves unresolved, rather than declaring the competing products insufficient.** One observed transfer alone does not account for three executed withdrawals. An empty source-hash search is a limited lookup result, not evidence of a competitor's full coverage or capabilities.

- Show the contribution: executed withdrawal counts and amounts checked against bridge records and destination logs, including grouped ambiguity and one-use transfer identities. Present these as demonstrated behavior, without claiming a novel algorithm or exclusive capability. Empty competitor search results do not establish superiority.
- Show the trust boundary: source and destination observations come through RPC providers; Chaindefuser supplies the cross-chain link and reported fee. Check the amounts against that evidence. Use “bridge-reported fee” and “provider observations”; never promise independent proof of the route, all fee causes or final settlement.
- Credit the public QA report as the starting case. The tool makes that investigation repeatable; it does not claim to have discovered the bug. Keep the complete report handoff as the current benefit. Payout lists, monitoring and more routes remain possible extensions, with adoption and competitive advantage unproven.

## Workspace and current product

- Product: `/home/alisa/Projects/ongoing/near/payout-reader`
- Video workspace: `/home/alisa/Projects/ongoing/near/payout-reader/video`
- Demo: https://payout-reader.up.railway.app
- Repository: https://github.com/Hesamation/wheres-the-rest
- Read the product's current AGENTS.md, README.md and project/STATUS.md; project/PLAN.md is historical. Record the actual product commit used for capture; do not assume the original brief's revision is current.
- Keep application code, imported reader, evidence and deployment unchanged. Video dependencies belong only under `video/`, isolated from the application runtime.
- Node, npm, FFmpeg, FFprobe, Chromium, UV and OBS were found installed. Remotion and voice dependencies were not installed for this task.

## 1. Rehearse and prepare narration

The human can do this manually or ask an agent to do it later.

First briefly rehearse Control, QA1, both explorer searches, evidence inspection and Copy Proof. Confirm the script’s actions and results can be shown before generating the full narration. Use the exact QA1 source hash in both explorers: `863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe`.

The November 14 public UI check returned “No results” in both [NEAR Intents Explorer](https://explorer.near-intents.org/?search=863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe) and [Range](https://explorer.range.org/transactions?sc=INTERCHAIN&s=863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe), with the hash visible and no additional filters selected. The script below reflects that observation. Capture fresh genuine searches for the video, label their date separately from the saved payout capture, and adjust the narration if their results change. If either returns a useful trace or reconciliation, show and credit it; explain only what remains unresolved. If a search fails to load, describe the failure rather than calling it “No results.”

**Optional voice audition — 10–15 seconds only:** test the voice with: “Executed. Great. Now show me what arrived. Three identical burns. Same recipient. One observed transfer. Where’s the rest?” Skip this test if the voice is already suitable. This short sample is not the finished narration.

Recommended manual starting point: https://aistudio.google.com/generate-speech, single speaker, voice Charon. Use an available free Gemini TTS model; the checked documentation listed `gemini-3.8-flash-tts`. Check free account availability; do not enable billing. Subscription access does not need to be assumed.

Delivery instructions, separate from spoken text:

> Conversational English. A confident builder showing someone an interesting discovery. Curious, slightly dry, with understated excitement. Natural variation in pace. Make “Great. Now show me what arrived” lightly challenging. Build anticipation through “three identical burns,” then pause before “Where’s the rest?” Deliver that question with curiosity. Around 135–145 words per minute, with room for pauses. Pronounce NEAR like “near,” Base normally, and USDC as individual letters. Read the narration verbatim.

**Final narration — the whole film:** paste the entire **Spoken script** block below, from “Executed” through “Follow the payout,” and generate it in one pass for consistency. This is the soundtrack for all main scenes, not just the opening. Regenerate individual paragraphs if needed. Download the highest-quality available audio, preferably WAV. Keep the original audio, exact spoken text, voice name and settings. Do not include stage directions in the spoken text. Measure the resulting duration before editing; the audition's length does not determine the final audio length.

Free fallback: local Kokoro-82M, voice `af_heart`, set up by the later agent if needed. Human narration can replace the same audio asset.

### Spoken script

```text
Executed.

Great. Now show me what arrived.

Start simple. One USDC withdrawn on NEAR. A bridge-reported fee.
Zero point nine nine seven six USDC observed on Base.

The amounts line up.

Now try three withdrawals.

In this public staging QA test on mainnet:
three identical burns. Same recipient.

One observed transfer.

Where’s the rest?

Cross-chain explorers already exist.
So we checked this source hash in NEAR Intents Explorer and Range.
Neither search returned a result for this hash.

Our payout question remains:
do all three withdrawals have matching evidence?

Where’s the Rest? checks the source burns,
bridge records and Base transfers in one read-only report.

Two burns have no matching bridge records in this saved capture.
The evidence can’t identify which identical burn matched.

So the report keeps them grouped.
One observed transfer gets counted once.
The unknowns stay visible.

Open the finding. Follow the receipt. Check the amounts.
The bridge reports the link and fee.
These are provider observations, not settlement proof.
Then share the report, with the evidence attached.

Replay a dated capture, or query the providers again.
Missing records don’t prove permanent loss.

Today, one public NEAR-to-Base USDC route.

Payout lists and ongoing monitoring are future work.

Where’s the Rest?

Follow the payout.
```

## 2. Set up production tools

Use Remotion with React/TypeScript and pinned dependencies, and Playwright for repeatable capture, all under `video/`. Reuse installed tools where possible. Consult official documentation or Remotion skills as needed; avoid global setup. Use local caption alignment only if needed. The supplied narration is ready: do not install a voice generator or regenerate it without a concrete need and human agreement. Shotcut is an optional free manual editor; normal finishing happens in Remotion.

Respect workspace instructions, including RTK shell command prefixes, no Astra, and no extra agents without explicit authorization. Keep credentials and downloaded models outside Git. No paid services or cloud rendering.

## 3. Capture and assemble around the audio

Measure the actual narration and fit scenes to it. Avoid padding to an arbitrary runtime. Capture genuine interactions in the unchanged local app, explicitly setting viewport and recording dimensions to 1920×1080. Retain raw clips and record the captured product commit and evidence dates.

| Beat | Picture |
|---|---|
| “Executed.” | Brief editorial title, followed by the actual workbench. |
| Successful payout | Click Control: 1.00 USDC. Enlarge **1.000000 − 0.002400 = 0.997600 USDC** and show matching evidence. Label the 0.002400 fee **bridge-reported**. |
| “Now try three withdrawals.” | Select QA1: Group Deficit. Show staging QA context and saved date. |
| Central reveal | Focus on **3 source burns / 1 observed / 2 unrecorded**. Pause, then introduce the project name as the question. |
| Check existing explorers | Show genuine QA1 source-hash searches in NEAR Intents Explorer and Range, with the same hash readable in both. Keep this to one brief comparison beat. Label **Public source-hash searches · capture date · limited lookup, not a full product comparison**. Show actual returned results; do not stage “No results” cards or imply these are application integrations. |
| The payout question remains | Return to **3 executed burns / 1 observed transfer**. Ask whether all withdrawals have matching evidence. This is the reason to reconcile the payout; avoid an unsupported claim that either product cannot do reconciliation. |
| Investigation | Show the grouped finding, source log identities, bridge record and destination transfer. Distinguish **NEAR RPC observation / bridge-reported link + fee / Base RPC observation** with editorial annotations. Keep “Provider observations, not final settlement” readable while inspecting the evidence. |
| Sharing | Follow the Base receipt link, return, click Copy Proof and briefly show its actual copied contents, including the evidence limitations. This is the completed payout-review handoff. |
| Saved and live | Show dated replay and Live Query prefill. Include a genuine fresh result if available; mark cuts through waiting time. Never substitute saved output as live. |
| Future direction | Keep this beat brief: **Today: one public NEAR → Base USDC route. Future: payout lists and ongoing monitoring.** Use a plain labelled card, then return to the workbench; do not show an unbuilt product screen. |
| Ending | Name, “Follow the payout,” demo and repository links, and “Built at NEAR HACKATHON.” Hold three seconds. |

Remotion combines narration, real footage/stills, animated crops/highlights/numbers/titles, and captions timed to speech. A subtle original electronic pulse may sit well below the narration and drop out at the central question; omit it if clarity suffers. Retain source/usage information for external assets.

Render and inspect a short opening preview before completing the full edit. Keep narration, captions, audio paths, shots and timing in an editable scene manifest. Individual lines and clips should be replaceable.

## 4. Verify and deliver

- Check every amount against the report. Keep saved dates, QA context and future labels visible. Preserve grouped attribution and unresolved findings.
- Check the explorer footage against the spoken result: same source hash, visible search value, capture date and actual output in each. Credit any useful returned evidence; retain the limited-comparison qualification.
- Check positioning against the current README: acknowledge existing tools, credit the reported QA case, label the bridge-reported fee and cross-chain link, and preserve provider-trust limits. No “first,” “only,” competitor incapability or original-bug-discovery claim. The roadmap is not part of the completed flow.
- Include a complete selection → result → evidence-inspection flow. Inspect actual Copy Proof contents.
- If live providers fail, show the real input action without fabricating a successful result; saved Control provides the completed investigation.
- Watch with sound, muted and at phone size. Enlarge important information. Correct captions against the script, especially amounts and names. Give the question and ending time to land.
- Confirm full narration runs across the film with only intentional short pauses. A 10–15 second audition followed by unplanned silence is not a finished soundtrack.
- Target narration around −16 LUFS, peaks below −1 dBTP.
- Export 1920×1080, 30 fps, H.264/AAC MP4, fast-start enabled, below 200 MB, maximum 120 seconds.
- Deliver captioned MP4, poster image, original narration, SRT, editable Remotion source/lockfile, raw captures and short render instructions.
- OBS can replace automated capture shots; human recordings can replace voice segments. Shotcut can handle manual finishing if required.

Publication is owned by the human. X post: say built at NEAR HACKATHON, include @NEARProtocol and #NEARHackathon, attach video and link demo/repository. Recheck current official rules before publication/submission. Deadline last checked: November 14, 2026 at 23:59 UTC. Keep demo available through judging. No repository visibility change, external posting or submission is authorized by this brief.

## Agent entry point

Read `START-HERE.md` in this directory for the local GLM handoff and production prompt. The original narration-generation instructions above are retained for reference; the supplied WAV is the production soundtrack.

## References

- Rules: https://nearhackathon.com/HACKATHON.md
- Public QA source: https://github.com/NEAR-DevHub/trezu/issues/1924
- Scope clarification: https://github.com/NEAR-DevHub/trezu/issues/1924#issuecomment-6744636005
- NEAR Intents Explorer API scope: https://docs.agentsonintents.com/integration/distribution-channels/1click-api/explorer/introduction
- Range NEAR Intents tracing: https://range.org/blog/near-intents-now-live-on-ranges-cross-chain-explorer
- Range reconciliation: https://range.org/product/transaction-reconciliation
- Remotion skills: https://www.remotion.dev/docs/ai/skills
- Gemini speech: https://ai.google.dev/gemini-api/docs/speech-generation
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Kokoro: https://huggingface.co/hexgrad/Kokoro-82M
- Shotcut: https://shotcut.org/
