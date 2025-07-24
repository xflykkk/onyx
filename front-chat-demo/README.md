# DeepInsight Chat Standalone

A beautiful, modern AI-powered document chat interface built with Next.js, React, and TypeScript. Features glassmorphism and neumorphic design styles with real-time streaming responses.

## ✨ Features

### 📁 Document Management
- **Drag & Drop Upload**: Intuitive file uploading with visual feedback
- **Multi-format Support**: PDF, DOC, TXT, images, spreadsheets, presentations, and more
- **Real-time Indexing**: Live status updates with progress indicators
- **File Management**: Organize, rename, and delete uploaded documents

### 💬 Intelligent Chat
- **Streaming Responses**: Real-time AI responses with typing effects
- **Document Search**: AI searches through your uploaded documents
- **Agent Mode**: Advanced search with sub-queries and research process
- **Citation Support**: Responses include source references and links

### 🎨 Modern Design
- **Glassmorphism**: Frosted glass effects with transparency and blur
- **Neumorphic**: Soft, tactile design with dual shadows
- **Responsive Layout**: Works seamlessly on desktop, tablet, and mobile
- **Dark/Light Mode**: Automatic theme switching support
- **Smooth Animations**: Framer Motion powered interactions

### 🔧 Technical Features
- **TypeScript**: Full type safety throughout the application
- **Real-time Streaming**: Server-Sent Events (SSE) for live responses
- **Error Handling**: Comprehensive error boundaries and recovery
- **Accessibility**: WCAG compliant with keyboard navigation
- **Performance**: Optimized rendering and memory management

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Onyx backend server running on `http://localhost:8080`

### Installation

1. **Clone and install dependencies**:
   ```bash
   cd onyx-chat-standalone
   npm install
   ```

2. **Configure environment**:
   ```bash
   # Create .env.local file
   echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8080" > .env.local
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser**:
   ```
   http://localhost:3000
   ```

### Backend Setup

Ensure the Onyx backend is running:

```bash
cd /Users/zhuxiaofeng/Github/onyx/backend
AUTH_TYPE=disabled /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m uvicorn onyx.main:app --reload --port 8080
```

## 📖 Usage Guide

### 1. Upload Documents

- **Drag & Drop**: Drop files directly onto the upload area
- **Click to Browse**: Click the upload area to select files
- **Supported Formats**: PDF, DOC/DOCX, TXT, CSV, images, and more
- **Batch Upload**: Upload multiple files simultaneously

### 2. Wait for Indexing

- Files are automatically processed and indexed
- Real-time status updates show indexing progress
- Only indexed files can be searched

### 3. Start Chatting

- Type questions about your documents
- AI will search through indexed content
- Get answers with source citations
- View search process in Agent mode

### 4. Advanced Features

- **File Selection**: Choose specific documents to search
- **Export Chat**: Download conversation history
- **Regenerate**: Get alternative responses
- **Search Progress**: Watch AI research process

## 🛠️ Development

### Project Structure

```
src/
├── app/                    # Next.js app router pages
│   ├── layout.tsx         # Root layout with global styles
│   └── page.tsx           # Main chat interface
├── components/            # React components
│   ├── ChatInterface.tsx  # Main chat component
│   ├── FileUpload.tsx     # File upload component
│   ├── MessageBubble.tsx  # Chat message display
│   └── SearchProgressDisplay.tsx # Search progress UI
├── hooks/                 # Custom React hooks
│   ├── useChat.ts         # Chat state management
│   └── useFileUpload.ts   # File upload logic
├── lib/                   # Utility libraries
│   ├── api.ts             # API client and SSE handling
│   ├── config.ts          # App configuration
│   ├── streaming.ts       # Streaming processors
│   └── utils.ts           # Helper functions
├── types/                 # TypeScript type definitions
│   └── index.ts           # All type definitions
└── styles/                # Global styles
    └── globals.css        # CSS with design system
```

### Key Technologies

- **Framework**: Next.js 15.2.4 with App Router
- **UI Library**: React 18.3.1 with TypeScript
- **Styling**: Tailwind CSS with custom design system
- **Animations**: Framer Motion for smooth interactions
- **File Upload**: React Dropzone with drag & drop
- **Markdown**: React Markdown for message rendering
- **Icons**: Lucide React icon library

### Design System

#### Glassmorphism Variables
```css
--glass-bg-light: rgba(255, 255, 255, 0.1);
--glass-bg-medium: rgba(255, 255, 255, 0.15);
--glass-bg-strong: rgba(255, 255, 255, 0.25);
--glass-border: rgba(255, 255, 255, 0.2);
```

#### Neumorphic Variables
```css
--neuro-bg: #e0e0e0;
--neuro-shadow-light: rgba(255, 255, 255, 0.8);
--neuro-shadow-dark: rgba(0, 0, 0, 0.2);
```

### Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server

# Code Quality
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript check

# Utilities
npm run analyze      # Analyze bundle size
npm run clean        # Clean build artifacts
```

## 🔌 API Integration

### Backend Endpoints

The application integrates with these Onyx backend APIs:

#### File Management
```typescript
POST /user/file/upload           # Upload files
GET  /user/file/indexing-status  # Check indexing status  
DELETE /user/file/{id}           # Delete file
POST /user/file/reindex          # Reindex file
```

#### Chat
```typescript
POST /chat/create-chat-session   # Create chat session
POST /chat/send-message          # Send message (SSE stream)
GET  /persona                    # Get available personas
```

### Streaming Protocol

The chat interface uses Server-Sent Events (SSE) for real-time responses:

```typescript
// Message types received via SSE
interface AnswerPiecePacket {
  answer_piece: string;
}

interface DocumentInfoPacket {
  document_id: string;
  document_name: string;
  // ... more fields
}

interface SubQueryPiece {
  sub_query: string;
  status: "todo" | "in_progress" | "done";
  // ... more fields  
}
```

## 🎨 Customization

### Design Variants

Switch between design styles in the settings panel:

- **Glassmorphism**: Frosted glass effects with transparency
- **Neumorphic**: Soft, extruded elements with dual shadows

### Theme Configuration

Modify design system in `src/lib/config.ts`:

```typescript
export const THEMES = {
  glassmorphism: {
    primary: 'rgba(255, 255, 255, 0.1)',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    // ... more properties
  },
  neumorphic: {
    primary: '#e0e0e0',
    background: 'linear-gradient(145deg, #e6e6e6, #ffffff)',
    // ... more properties
  },
};
```

### Custom Animations

Add custom animations in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      animation: {
        'custom-float': 'float 6s ease-in-out infinite',
        'custom-glow': 'glow 2s ease-in-out infinite alternate',
      },
    },
  },
};
```

## 🚦 Error Handling

### Error Boundaries

The application includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Upload Errors**: File validation and detailed error messages  
- **Streaming Errors**: Graceful degradation and error recovery
- **UI Errors**: Error boundaries prevent app crashes

### Debugging

Enable debug mode by setting:

```bash
LOG_LEVEL=DEBUG npm run dev
```

## 📱 Progressive Web App

The application includes PWA features:

- **Offline Support**: Basic offline functionality
- **Install Prompt**: Add to home screen capability
- **App Manifest**: Native app-like experience
- **Service Worker**: Background updates and caching

## 🔒 Security

### Best Practices

- **Input Validation**: All user inputs are validated
- **XSS Protection**: Markdown rendering is sanitized
- **CSRF Protection**: API requests include proper headers
- **Content Security Policy**: Restricts resource loading

### File Upload Security

- **Type Validation**: Only allowed file types accepted
- **Size Limits**: Maximum file size enforcement
- **Sanitization**: File names and content are sanitized

## 🚀 Deployment

### Production Build

```bash
npm run build
npm run start
```

### Environment Variables

```bash
# Required
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080

# Optional
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

### Docker Deployment

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

### Code Standards

- **TypeScript**: Use strict type checking
- **ESLint**: Follow configured rules
- **Prettier**: Auto-format code
- **Conventional Commits**: Use standard commit messages

### Testing

```bash
npm run test           # Run unit tests
npm run test:e2e       # Run end-to-end tests
npm run test:coverage  # Generate coverage report
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Onyx Team**: For the powerful backend API
- **DeepInsight Team**: For the frontend implementation
- **Vercel**: For Next.js framework
- **Tailwind Labs**: For Tailwind CSS
- **Framer**: For Motion animations
- **Lucide**: For beautiful icons

## 📞 Support

- **Documentation**: Check this README and inline comments
- **Issues**: Report bugs via GitHub issues  
- **Discussions**: Ask questions in GitHub discussions
- **Email**: Contact the development team

---

Built with ❤️ using Next.js, React, and TypeScript