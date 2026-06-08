# Enable the Claude in Chrome extension

The Owner Mailing List skill pulls county parcel data through your browser, so it needs the **Claude in Chrome** extension enabled in Claude Desktop. This is a one-time, in-session step — no account signup, no email confirmation, no loopback listener.

> Note: this is the **Claude in Chrome** extension, not "Control Chrome." If you have both, the skill uses Claude in Chrome.

---

## Steps

### 1. Open Claude Desktop Settings

In the Claude Desktop app, click the gear icon (Settings) in the bottom-left corner of the sidebar — or use the menu: **Claude → Settings**.

![screenshot: Claude Desktop with the gear/settings icon highlighted in the bottom-left sidebar](placeholder-01-settings-icon.png)

---

### 2. Go to Extensions and enable Claude in Chrome

In the Settings panel, click **Extensions** in the left nav. You should see **Claude in Chrome** listed. Click the toggle to turn it **on**.

![screenshot: Settings → Extensions panel with "Claude in Chrome" listed and the toggle in the ON position](placeholder-02-extensions-toggle.png)

If you don't see Claude in Chrome in the list, the extension may not be installed yet. Contact your GI workspace admin (David or Bonner) to get it added to your account.

---

### 3. Confirm it's working

Close Settings, open a Chrome window, and ask Claude:

> Open google.com for me.

Claude should respond by opening `https://www.google.com` in your Chrome window. If it does, the extension is active and the Owner Mailing List skill will work.

![screenshot: Claude chat with the message "Open google.com for me" and Claude's confirmation that it opened the URL](placeholder-03-confirm-open-url.png)

---

## Once confirmed

Come back to your owner mailing list request and Claude will run the county parcel pull automatically. A typical pull takes 60–180 seconds depending on the county and how many parcels match.

---

## Troubleshooting

**The Claude in Chrome toggle is missing from Extensions.**
The extension isn't installed on your account. Ask David or Bonner to add it — it takes about 2 minutes from the admin side.

**Claude says it opened the URL but nothing happened in my browser.**
Make sure Chrome is open with at least one window before you run the request — Claude in Chrome attaches to an open Chrome tab.

**I see an error after enabling the toggle.**
Try closing and reopening Claude Desktop, then re-check Extensions. If the toggle shows ON but the skill still halts at Step 0, open a fresh Chrome tab and try again.
