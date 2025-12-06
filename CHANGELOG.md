# Changelog

All notable changes to TravelMind will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Request ID middleware for request tracing and debugging
- Detailed health check endpoint with system resource monitoring
- E2E tests with Playwright
- GDPR-compliant user data export (Article 20 compliance)
- Password reset flow with JWT-based email verification
- Database backup scripts (SQLite & PostgreSQL)
- Production Docker builds with multi-stage optimization
- Production docker-compose with Redis cache and auto-backup
- Deployment script for easy production deployments
- **Multi-language support**: Added French and Spanish translations
- **Namespace-based i18n**: Migrated to namespace-based translation system
- **Lightbox**: Full-screen image viewing in diary entries with keyboard navigation
- **Expandable diary entries**: "Read more" functionality for long entries
- **IndexedDB fallback**: Graceful handling when IndexedDB is unavailable

### Changed
- Centralized rate limiting configuration
- Enhanced OpenAPI documentation with examples
- Improved i18n architecture with 25 separate namespace files per language
- LanguageSwitcher now dynamically loads available languages

### Fixed
- Settings page "t is not defined" error
- Diary "Weiterlesen" button not working
- IndexedDB "open is not a function" error in certain environments

### Security
- Added audit logging for sensitive operations
- Improved rate limiting per endpoint

## [1.0.0] - 2025-01-15

### Added
- Initial release of TravelMind
- User authentication with JWT
- Trip management (CRUD operations)
- Travel diary with photos and mood tracking
- Places/POI management with GPS coordinates
- Budget and expense tracking
- Timeline view for trip activities
- Multi-provider AI integration (Groq, Claude, OpenAI, Gemini)
- User-configurable AI API keys
- Multi-language support (German, English)
- Responsive web interface
- Docker containerization
- PostgreSQL and SQLite support

### Security
- JWT-based authentication
- Password hashing with bcrypt
- API key encryption
- CORS configuration
- Security headers middleware
- CSRF protection
- Request size limits

### Documentation
- OpenAPI/Swagger documentation
- README with setup instructions
- CONTRIBUTING guidelines
- Environment variable documentation

---

## Version History

### Legend
- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes

[Unreleased]: https://github.com/your-repo/TravelMind/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-repo/TravelMind/releases/tag/v1.0.0
