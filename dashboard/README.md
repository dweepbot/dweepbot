# DweepBot Pro Dashboard

Real-time web dashboard for monitoring and controlling DweepBot autonomous agents.

## Commercial License Required

This dashboard is part of DweepBot Pro and requires a commercial license.
See [LICENSE-COMMERCIAL.md](../LICENSE-COMMERCIAL.md) for details.

## Features

- **Real-time Monitoring**: Live agent status and execution streams
- **Cost Tracking**: Real-time token usage and cost analytics
- **Multi-Agent View**: Monitor multiple agents simultaneously
- **Tool Execution Logs**: Detailed logs of all tool invocations
- **Performance Metrics**: Zero-shot success rates, context efficiency
- **Agent Control**: Start, stop, and configure agents from the dashboard

## Installation

```bash
cd dashboard
npm install
```

## Development

```bash
# Start development server
npm run dev

# Build for production
npm run build
```

## Configuration

The dashboard connects to the DweepBot Pro API backend (api_server.py).

Default configuration:
- API URL: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws/{agent_id}`

## License

Copyright © 2026 DweepBot Inc. All rights reserved.

This dashboard requires a valid DweepBot Pro license.
Visit https://dweepbot.com/pro to get your license.
