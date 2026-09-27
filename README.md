# DocuMind AI

> An AI-powered document and knowledge assistant that allows users to upload documents, search their content using semantic similarity, ask context-aware questions, and generate useful learning materials from their documents.

---

## 📌 Overview

**DocuMind AI** is a full-stack AI document assistant designed to make it easier to understand, search, and interact with documents.

Instead of manually searching through long PDF or DOCX files, users can upload their documents and ask questions about their contents.

DocuMind AI processes uploaded documents, extracts their text, divides the content into smaller chunks, creates AI embeddings, and uses semantic similarity search to find the most relevant information.

The relevant document content is then provided to the AI model so that it can generate a context-aware answer.

The system also provides additional AI-powered tools such as:

- Document summaries
- Key points
- Flashcards
- Quiz generation
- Source citations
- Multi-document questions
- Conversation history

DocuMind AI is currently designed as a lightweight, local-first application and does not require user authentication.

---

# ✨ Features

## 📄 Document Management

Users can:

- Upload PDF files
- Upload DOCX files
- View uploaded documents
- Search documents
- Download documents
- Delete documents
- View document metadata
- View document processing information

### Supported formats

| File Type | Supported |
|---|---|
| PDF | ✅ |
| DOCX | ✅ |
| DOC | ❌ |
| TXT | ❌ |
| PPTX | ❌ |
| XLSX | ❌ |

### Upload limit

The current maximum upload size is:

```text
10 MB