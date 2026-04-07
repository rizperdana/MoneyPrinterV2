### Rewritten Instruction (for local agent)

Project Status

* The project is partially completed.
* Current issues:

  * Execution is not persistent over long runs.
  * Stability problems (bugs appear during extended operation).
  * Latest commit supports YouTube upload, but uploads are incorrectly set to *private* instead of *public*.

---

### Objective

Run, test, and continue development until the system can:

* Reliably generate content.
* Automatically publish content to:

  * YouTube
  * TikTok
  * Facebook
* Operate continuously with minimal errors and stable long-term performance.

---

### Browser / Profile

* Use existing Firefox profile:


  /home/anon/.mozilla/firefox/1gb196dc.default-release

* Confirm ability to launch and browse using this profile.

---

### Platform Upload Targets

#### YouTube

* URL:


  https://studio.youtube.com/channel/UCFhX7gLJhz7cBMSzIdSgpqg

* Requirements:

  * Upload video
  * Ensure visibility is set to Public (not Private)

#### TikTok

* URL:


  https://www.tiktok.com/tiktokstudio/upload?from=webapp

* Upload via web studio

#### Facebook

* Behavior:

  * Automatically opens page profile after login
  * Upload directly from homepage interface

---

### LLM / Media Stack

* LLM provider: cliproxyapi

  * Preferred model: kilo-auto/free
  * Fallback: any available free model
* Image generation:

  * Prioritize Cloudflare models
* Text-to-Speech:

  * Use Edge TTS as primary option

---

### Execution Requirements

#### Upload Flow

* Uploads must be sequential:

  1. Upload to one platform
  2. If success:

     * Store resulting URL
  3. If failure:

     * Store error details
  4. Proceed to next platform

---

#### Post-Execution Cleanup

* After all uploads:

  * Close browser
  * Clear /tmp directory (if exists)

---

### Performance Constraints

* Ensure:

  * Low memory usage
  * Minimal disk usage
  * Efficient execution (avoid resource leaks)

---

### Success Criteria

* System can:

  * Run continuously without crashing
  * Handle failures gracefully
  * Successfully upload and publish content (public visibility where applicable)
  * Log results (URLs or errors) for each platform
