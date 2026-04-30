# RomDynamics Bot — Workflows

## 1. Overall Bot Command Flow

```mermaid
flowchart TD
    U([User sends message]) --> Q1{Command or\nplain text?}

    Q1 -->|/start or /help| USAGE[Show USAGE_TEXT]
    Q1 -->|/ping| PONG[Reply: pong]
    Q1 -->|/do_auth| AUTH_START[Ask: Who are you?\nSet awaiting_auth_reply=true]
    Q1 -->|/do_ytmp3cvt| YT_CMD[cmd_do_ytmp3cvt]
    Q1 -->|plain text| MSG_HANDLER[handle_text_messages]
```

---

## 2. Authentication Flow

```mermaid
flowchart TD
    A([/do_auth command]) --> B[Reply: Who are you?\nawaiting_auth_reply = true]
    B --> C([User sends username])
    C --> D{awaiting_auth_reply\n== true?}
    D -->|No| IGNORE[Ignored / falls through]
    D -->|Yes| E[awaiting_auth_reply = false]
    E --> F{Username matches\nAUTHORIZED_USERNAME?}
    F -->|Yes| G[is_authorized = true\nlast_activity = now\nReply: Authorized]
    F -->|No| H[is_authorized = false\nReply: Unauthorized]
```

---

## 3. YouTube MP3 Download Flow — via Command Args

```mermaid
flowchart TD
    A([/do_ytmp3cvt URL]) --> B{is_authorized?\nNot expired?}
    B -->|No| C[Reply: Unauthorized or session expired]
    B -->|Yes| D[last_activity = now]
    D --> E{Valid YouTube URL?}
    E -->|No| F[Reply: Invalid URL]
    E -->|Yes| G[process_youtube_link]
    G --> H[Reply: Downloading...]
    H --> I[run_in_executor\ndownload_youtube_video]
    I --> J{yt-dlp\nsucceeded?}
    J -->|No| K[Reply: Download error message]
    J -->|Yes| L{File size\n≤ 50 MB?}
    L -->|No| M[Delete file\nReply: File too large]
    L -->|Yes| N[Reply: Sending audio...]
    N --> O[reply_audio to user]
    O --> P[last_activity = now\nDelete temp file]
```

---

## 4. YouTube MP3 Download Flow — via Awaiting Link

```mermaid
flowchart TD
    A([/do_ytmp3cvt — no args]) --> B{is_authorized?\nNot expired?}
    B -->|No| C[Reply: Unauthorized]
    B -->|Yes| D[last_activity = now\nawaiting_youtube_link = true\nReply: Send YouTube link]
    D --> E([User sends URL as plain text])
    E --> F{awaiting_youtube_link\n== true?}
    F -->|No| IGNORE[Falls through / ignored]
    F -->|Yes| G[awaiting_youtube_link = false]
    G --> H{is_authorized?\nNot expired?}
    H -->|No| I[is_authorized = false\nReply: Session expired]
    H -->|Yes| J[last_activity = now]
    J --> K{Valid YouTube URL?}
    K -->|No| L[Reply: Invalid URL]
    K -->|Yes| M[process_youtube_link]
    M --> N[Reply: Downloading...]
    N --> O[run_in_executor\ndownload_youtube_video]
    O --> P{yt-dlp\nsucceeded?}
    P -->|No| Q[Reply: Download error message]
    P -->|Yes| R{File size\n≤ 50 MB?}
    R -->|No| S[Delete file\nReply: File too large]
    R -->|Yes| T[Reply: Sending audio...]
    T --> V[reply_audio to user]
    V --> W[last_activity = now\nDelete temp file]
```

---

## 5. Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated

    Unauthenticated --> AwaitingAuth : /do_auth
    AwaitingAuth --> Authenticated : correct username
    AwaitingAuth --> Unauthenticated : wrong username

    Authenticated --> AwaitingYouTubeLink : /do_ytmp3cvt (no args)
    AwaitingYouTubeLink --> Authenticated : URL received & processed
    AwaitingYouTubeLink --> Unauthenticated : session timeout (10 min)

    Authenticated --> Unauthenticated : session timeout (10 min)
    Authenticated --> Authenticated : activity refreshes last_activity
```
