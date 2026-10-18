# Integration state

The implemented paid route is Meshy Creative Lab Brick Figure v1, with separate prototype and build stages. CLI passthrough uses `/brick-figure/v1/prototype` and `/brick-figure/v1/build` under `--creative-lab`; the resulting REST paths begin `/openapi/creative-lab/`. Prototype accepts `image_url`, `name`, `remove_background`; build accepts `input_task_id` and `name`. Never add a prompt field. Nominal prices checked 2026-10-18: 6 and 30 credits; refresh official pricing before new spend.

The full research matrix is maintained in the governed Drive hub. Meshy 7.1, Text/Image/Multi-Image-to-3D, PBR retexture, Smart Topology T2.5, remesh, UV, resize, rigging, animation and printing APIs are documented separately; their discovery does not imply end-to-end implementation here.

Official Meshy MCP Creative Lab can combine prototype and build automatically. Do not use that combined flow where visual approval is required. API assets normally have three-day retention; save them with hashes promptly and retain lineage. Never regenerate merely to work around asset expiry or transfer errors.

Primary sources: [Meshy API](https://docs.meshy.ai/), [pricing](https://docs.meshy.ai/en/api/pricing), [Brick Figure](https://docs.meshy.ai/en/api/creative-lab-brick-figure), [OpenAI tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
