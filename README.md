# StringDB-Link

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

High-performance unified API server for the STRING protein-protein interaction database with both REST API and MCP (Model Context Protocol) support.

## 🚀 Features

- **Dual Protocol Support**: Both HTTP REST API and MCP for AI applications
- **Comprehensive Coverage**: All major STRING API endpoints
- **High Performance**: Async/await throughout with intelligent caching
- **Type Safety**: Complete type hints with Pydantic validation
- **Rate Limiting**: Respects STRING's API rate limits
- **Error Resilience**: Retry logic with exponential backoff
- **Claude Desktop Ready**: Seamless integration with Claude Desktop

## 📋 Supported STRING Operations

### Core Functionality
- **Protein Identifier Resolution**: Map gene names, UniProt IDs to STRING identifiers
- **Network Interactions**: Retrieve protein-protein interaction networks
- **Interaction Partners**: Get all interaction partners for proteins
- **Functional Enrichment**: Gene Ontology and pathway enrichment analysis
- **Functional Annotations**: Protein annotations from multiple databases
- **Network Visualization**: Generate protein network images (PNG/SVG)

### Advanced Features
- **Homology Analysis**: Protein similarity scores and cross-species homology
- **PPI Enrichment**: Statistical analysis of interaction networks
- **Enrichment Visualization**: Generate enrichment analysis figures
- **Web Links**: Direct links to STRING website networks

## 🛠️ Installation

### From Source
```bash
git clone https://github.com/stringdb-link/stringdb-link.git
cd stringdb-link
pip install -e ".[dev]"
```

### Using pip (when published)
```bash
pip install stringdb-link
```

## ⚡ Quick Start

### Start HTTP Server
```bash
stringdb-link server --host 0.0.0.0 --port 8000
```

### Start MCP Server (for Claude Desktop)
```bash
stringdb-link mcp
```

### Start Unified Server (HTTP + MCP)
```bash
stringdb-link server --transport unified --port 8000
```

## 🔧 Configuration

Create a `.env` file or set environment variables:

```bash
# Server Configuration
HOST=127.0.0.1
PORT=8000
TRANSPORT=unified
ALLOWED_HOSTS=["localhost","127.0.0.1","::1"]
ALLOWED_ORIGINS=[]

# StringDB API Configuration
STRINGDB_BASE_URL=https://version-12-0.string-db.org/api
STRINGDB_RATE_LIMIT_DELAY=1.0

# Caching Configuration
CACHE_ENABLED=true
CACHE_IDENTIFIER_TTL=86400  # 24 hours
CACHE_NETWORK_TTL=43200     # 12 hours

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

HTTP deployments enforce exact Host and Origin allowlists. Add the public
reverse-proxy hostname to `ALLOWED_HOSTS`; wildcard host patterns are rejected.
`ALLOWED_ORIGINS=[]` permits requests without an `Origin` header. These request
guards are independent of the separate `CORS__ALLOW_ORIGINS` response policy.

## 📚 API Usage Examples

### Resolve Protein Identifiers
```bash
curl -X POST "http://localhost:8000/api/identifiers/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "identifiers": ["p53", "BRCA1", "cdk2"],
    "species": 9606,
    "echo_query": true
  }'
```

### Get Protein Interactions
```bash
curl -X POST "http://localhost:8000/api/networks/interactions" \
  -H "Content-Type: application/json" \
  -d '{
    "identifiers": ["TP53", "MDM2", "ATM"],
    "species": 9606,
    "required_score": 400,
    "network_type": "functional"
  }'
```

### Functional Enrichment Analysis
```bash
curl -X POST "http://localhost:8000/api/enrichment/functional" \
  -H "Content-Type: application/json" \
  -d '{
    "identifiers": ["TP53", "MDM2", "ATM", "CHEK2", "BRCA1"],
    "species": 9606
  }'
```

## 🤖 MCP Integration (Claude Desktop)

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "stringdb-link": {
      "command": "stringdb-link",
      "args": ["mcp"],
      "env": {
        "STRINGDB_RATE_LIMIT_DELAY": "1.0"
      }
    }
  }
}
```

### Available MCP Tools

Tool names follow the [GeneFoundry Tool-Naming Standard v1](#tool-naming-standard)
(`verb_noun` snake_case, canonical verb, unprefixed):

- `resolve_protein_identifiers`: Map protein names/symbols to STRING IDs
- `search_protein_interactions`: Find protein network interactions
- `get_interaction_partners`: Get interaction partners for proteins
- `get_network_link`: Get a shareable STRING network view URL
- `compute_functional_enrichment`: Run STRING functional enrichment analysis
- `compute_ppi_enrichment`: Run STRING protein-protein interaction enrichment test
- `get_functional_annotations`: Retrieve STRING functional annotations
- `get_protein_homology_scores`: Get cross-species homology bit-scores
- `get_protein_homology_best_hits`: Get best cross-species homology hits
- `get_network_image`: Get a STRING network visualization image

### Tool-Naming Standard

This server is part of the **GeneFoundry MCP router** (`genefoundry-router`) fleet.

- **`serverInfo.name`** is set explicitly to `StringDB-Link Server`.
- **Canonical gateway namespace token: `stringdb`.** Leaf tools are exposed
  *unprefixed*; the router applies the namespace at mount time, so tools surface
  at the gateway as `stringdb_<tool>` (e.g. `stringdb_search_protein_interactions`).
  Do **not** add a `stringdb_` self-prefix to tool names — that would
  double-prefix at the gateway.

A CI guard (`tests/unit/test_tool_names.py`) asserts that every registered tool
matches `^[a-z0-9_]{1,50}$`, starts with a canonical verb
(`get`/`search`/`list`/`resolve`/`find`/`compare`/`compute`), and does not
self-prefix the `stringdb` namespace token.

## 🧪 Development

### Setup Development Environment
```bash
git clone https://github.com/stringdb-link/stringdb-link.git
cd stringdb-link
pip install -e ".[dev]"
pre-commit install
```

### Run Tests
```bash
pytest
```

### Run Linting
```bash
ruff check .
ruff format .
mypy .
```

### Check Configuration
```bash
stringdb-link validate-config
```

### Health Check
```bash
stringdb-link health
```

## 📖 API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🏗️ Architecture

StringDB-Link follows a clean architecture pattern:

```
├── api/                    # HTTP client and route handlers
│   ├── client.py          # StringDB HTTP client with caching
│   └── routes/            # FastAPI route definitions
├── models/                # Pydantic data models
│   ├── requests.py        # Request validation models
│   ├── responses.py       # Response serialization models
│   └── stringdb.py        # StringDB-specific enums and constants
├── services/              # Business logic layer
├── utils/                 # Shared utilities
├── config.py              # Configuration management
├── exceptions.py          # Custom exception classes
└── logging_config.py      # Structured logging setup
```

## 📊 Performance

- **Response Time**: < 2 seconds for most queries
- **Cache Hit Rate**: > 80% for repeated queries
- **Concurrent Requests**: Supports 100+ concurrent requests
- **Memory Usage**: Efficient with configurable cache limits

## 🔒 Security

- Input validation with Pydantic models
- Rate limiting to prevent abuse
- No sensitive data logging
- Optional API key authentication
- CORS configuration for web apps

See [`SECURITY.md`](SECURITY.md) for the vulnerability-reporting process and the
required repository settings (secret scanning / push protection) an operator must enable.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Run linting (`ruff check . && mypy .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [STRING Database](https://string-db.org/) for providing the comprehensive protein interaction data
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [FastMCP](https://github.com/jlowin/fastmcp) for MCP integration
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/stringdb-link/stringdb-link/issues)
- **Documentation**: [Full Documentation](https://stringdb-link.readthedocs.io)
- **Email**: dev@stringdb-link.org

---

Made with ❤️ for the scientific community
