# HappyHorse live verification

Model: `happyhorse-1.1-r2v`, using the existing Token Plan configuration.

Verified on 2026-09-09:

- A real reference-image generation task succeeded: `361ceb5b-d40c-4e4a-94c4-7a77fa91e3e6`.
- Corrected task polling to send Authorization only. Sending `X-DashScope-Async: enable` to the polling endpoint caused the asynchronous-call error.
- Queried the successful task again through the corrected HappyHorseClient.poll implementation.
- Downloaded the actual provider output to `outputs/live-tests/happyhorse-real-5s.mp4` (2,015,524 bytes).
- FFmpeg inspected the file: 720x1280 H.264, 24 fps, approximately 5.16 seconds, stereo AAC audio at 44100 Hz.

This proves provider submission, reference input, polling and result download. It does NOT yet prove the complete CreatorOS acceptance workflow.

Remaining checks and fixes:

- video_generator currently forces a five-second duration, which is suitable only for this connectivity test; full dialogue requires duration handling or per-shot generation and composition.
- The sample prompt requested a waving character and no text. Audio-track presence does not prove intelligible requested dialogue, and this sample does not validate subtitles.
- Verify two named role references, original dialogue, subtitles and full shot sequence.
- Verify browser progress, refresh recovery, persisted provider task IDs and download through the application.
- Revalidate real-video reverse analysis, including audio evidence rather than assuming keyframes contain speech.

Do not mark all acceptance criteria passed based on this connectivity test.
