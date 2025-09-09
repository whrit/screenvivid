diff --git a/README.md b/README.md
index 49b9c4955246d503329f1984dadd3514f5063be0..c7bc764691ea0cac74f9db8536e3a52a8b07432f 100644
--- a/README.md
+++ b/README.md
@@ -4,50 +4,51 @@
   # ScreenVivid
 
   [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
   [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/tamnguyenvan/screenvivid/releases)
   [![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
   [![Downloads](https://img.shields.io/github/downloads/tamnguyenvan/screenvivid/total.svg)](https://github.com/tamnguyenvan/screenvivid/releases)
   [![Discord](https://img.shields.io/discord/1234567890?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/NKtmBnR6nE)
 
   <p><em>Simple, powerful screen recording for everyone</em></p>
 </div>
 
 <div align="center">
   <img src="./assets/hero.png" alt="ScreenVivid UI Showcase" width="80%">
 </div>
 
 ## 🚀 Overview
 
 [ScreenVivid](https://screenvivid.com) is a simple and user-friendly screen recording application with intuitive editing features. Capture tutorials, meetings, or gameplay with ease on any platform!
 
 ## ✨ Features
 
 - **💻 Cross-platform support** - Available on Windows, macOS, and Linux
 - **🎥 High-quality recording** - Professional-looking video capture
 - **🔧 Video enhancement tools** - Add backgrounds, padding, and more
 - **🎨 Intuitive interface** - Start recording with just a few clicks
+- **🔍 Auto-zoom & click highlighting** - Emphasize cursor actions ([guide](docs/auto-zoom-click-highlighting.md))
 - **🆓 Free and open-source** - No hidden costs or limitations
 
 ## 📥 Installation
 
 ### System Requirements
 
 | Platform | Requirements |
 |----------|-------------|
 | Windows | Windows 10+, 4GB RAM (8GB recommended) |
 | macOS | macOS 11.0+, 4GB RAM (8GB recommended) |
 | Linux | Python 3.9+, glibc 2.28+, X11, 4GB RAM (8GB recommended) |
 
 ### 🐧 Linux
 
 ```bash
 # Ubuntu/Debian
 sudo dpkg -i screenvivid-x.x.x-amd64.deb
 sudo apt install -f  # If missing dependencies
 ```
 
 ### 🪟 Windows
 
 1. Download the latest installer from [Releases](https://github.com/tamnguyenvan/screenvivid/releases)
 2. Run the installer (click through security warnings)
 3. Launch from Start Menu or Desktop shortcut
diff --git a/README.md b/README.md
index 49b9c4955246d503329f1984dadd3514f5063be0..c7bc764691ea0cac74f9db8536e3a52a8b07432f 100644
--- a/README.md
+++ b/README.md
@@ -94,50 +95,54 @@ pip install "pyobjc-framework-Quartz>=10.3.1,<10.4" "pyobjc-framework-UniformTyp
 pip install "pywin32>=306,<308" && pip install -r requirements.txt
 ```
 
 #### 3. Compile and Run
 
 ```bash
 cd screenvivid
 python compile_resources.py
 python -m screenvivid.main
 ```
 </details>
 
 ## 💪 Advantages
 
 - **👍 Easy to use** - Intuitive interface for all skill levels
 - **🌍 Cross-platform** - Works on your preferred operating system
 - **💯 High quality** - Crystal clear screen recordings
 - **🆓 Always free** - No premium tiers or hidden costs
 
 ## ⚠️ Current Limitations
 
 - No audio capture or webcam integration yet
 - Application size is larger than optimal
 - Advanced editing features still in development
 
+## 🔍 Auto-Zoom & Click Highlighting
+
+ScreenVivid can focus on important actions by automatically zooming near the cursor and highlighting mouse clicks. These effects work on Windows, macOS, and Linux but require additional processing. Lower resolutions or disabling the features can improve performance on slower hardware. Learn more in the [Auto-Zoom & Click Highlighting Guide](docs/auto-zoom-click-highlighting.md).
+
 ## ❓ FAQ
 
 <details>
 <summary><b>Is ScreenVivid free?</b></summary>
 Yes! ScreenVivid is completely free and open-source.
 </details>
 
 <details>
 <summary><b>Is it safe despite security warnings?</b></summary>
 Yes. We haven't obtained a code signing certificate yet (budget constraints), but our software is safe to use.
 </details>
 
 <details>
 <summary><b>How can I contribute?</b></summary>
 We welcome contributions! Check our GitHub repository or contact us directly.
 </details>
 
 <details>
 <summary><b>Missing packages when installing on Linux?</b></summary>
 Run <code>sudo apt install -f</code> to install missing dependencies.
 </details>
 
 ## 🗺️ Roadmap
 
 - [ ] 🎤 Audio capture support
