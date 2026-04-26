import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add root and backend to path
root_dir = Path(__file__).parents[2]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from packages.ingestion.semantic_splitter import SemanticSplitter

class TestSemanticSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = SemanticSplitter(threshold=0.5, max_tokens=10)

    @patch('packages.ingestion.semantic_splitter.get_embeddings')
    def test_split_text_semantic(self, mock_embeddings):
        # Mock embeddings: first two sentences are similar, third is different
        # Vector [1, 0] and [0.9, 0.1] are similar (> 0.5)
        # Vector [0, 1] is different (< 0.5)
        mock_embeddings.return_value = [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0]
        ]
        
        text = "Sentence one. Sentence two. Sentence three."
        chunks = self.splitter.split_text(text)
        
        # Should split into two chunks: 
        # 1: "Sentence one. Sentence two."
        # 2: "Sentence three."
        self.assertEqual(len(chunks), 2)
        self.assertIn("Sentence one. Sentence two.", chunks[0])
        self.assertEqual("Sentence three.", chunks[1])

    @patch('packages.ingestion.semantic_splitter.get_embeddings')
    def test_fallback_splitter(self, mock_embeddings):
        # Mock embeddings to be very similar so it doesn't split semantically
        mock_embeddings.return_value = [[1.0, 0.0]] * 5
        
        # Very long text that exceeds max_tokens (10)
        text = "This is a very long sentence that will definitely exceed the token limit of ten tokens."
        
        # The splitter should see this as one semantic chunk, then apply fallback
        chunks = self.splitter.split_text(text)
        
        # Should have more than 1 chunk due to fallback
        self.assertTrue(len(chunks) > 1)

if __name__ == '__main__':
    unittest.main()
