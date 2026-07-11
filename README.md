<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polisim - 分层驱动的多实体仿真引擎</title>
    <style>
        :root {
            --bg-primary: #050506;
            --bg-secondary: #0c0d0e;
            --bg-tertiary: #1c1c1f;
            --text-primary: #f7f8f8;
            --text-secondary: #d0d6e0;
            --text-tertiary: #8a8f98;
            --accent: #7170ff;
            --accent-hover: #828fff;
            --border: #23252a;
            --font-sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: var(--font-sans);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            max-width: 600px;
            width: 100%;
            text-align: center;
        }

        .logo {
            font-size: 4rem;
            font-weight: 700;
            margin-bottom: 16px;
            background: linear-gradient(135deg, var(--accent), #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .tagline {
            font-size: 1.25rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .description {
            font-size: 1rem;
            color: var(--text-tertiary);
            margin-bottom: 48px;
        }

        .language-card {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .lang-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 20px 32px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 1.125rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .lang-btn:hover {
            border-color: var(--accent);
            background-color: var(--bg-tertiary);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(113, 112, 255, 0.2);
        }

        .lang-btn:active {
            transform: translateY(0);
        }

        .lang-flag {
            font-size: 1.5rem;
        }

        .lang-info {
            text-align: left;
        }

        .lang-title {
            display: block;
            font-weight: 600;
        }

        .lang-subtitle {
            display: block;
            font-size: 0.875rem;
            color: var(--text-tertiary);
            margin-top: 2px;
        }

        .footer {
            margin-top: 48px;
            font-size: 0.875rem;
            color: var(--text-tertiary);
        }

        .footer a {
            color: var(--accent);
            text-decoration: none;
        }

        .footer a:hover {
            color: var(--accent-hover);
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Polisim</div>
        <div class="tagline">分层驱动的多实体仿真引擎</div>
        <div class="description">Layered LLM-driven multi-agent simulation engine</div>
        
        <div class="language-card">
            <a href="README.zh-CN.md" class="lang-btn">
                <span class="lang-flag">🇨🇳</span>
                <span class="lang-info">
                    <span class="lang-title">简体中文</span>
                    <span class="lang-subtitle">Chinese (Simplified)</span>
                </span>
            </a>
            
            <a href="README.en.md" class="lang-btn">
                <span class="lang-flag">🇺🇸</span>
                <span class="lang-info">
                    <span class="lang-title">English</span>
                    <span class="lang-subtitle">English (US)</span>
                </span>
            </a>
        </div>

        <div class="footer">
            <p>GitHub: <a href="https://github.com/Kaka-cheaper/Polisim" target="_blank">Kaka-cheaper/Polisim</a></p>
            <p class="mt-2">MIT License · Python 3.10+</p>
        </div>
    </div>
</body>
</html>