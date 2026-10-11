from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'extension/bridge.js').read_text(encoding='utf8')
header='''// ==UserScript==
// @name         KAI Harvester Bridge (experimental)
// @namespace    https://github.com/KAI-harvester-fusion
// @version      0.1.0
// @description  Opt-in local JSON backup, no remote server, for own ChatGPT data.
// @match        https://chatgpt.com/*
// @grant        none
// @run-at       document-idle
// @license      MIT
// ==/UserScript==

'''
path=root/'userscript/KAI_Harvester.user.js'
path.write_text(header+source,encoding='utf8')
print(path)
