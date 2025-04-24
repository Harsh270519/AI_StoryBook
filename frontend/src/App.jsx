import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [numPages, setNumPages] = useState(3);
  const [storyPages, setStoryPages] = useState([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [translateLang, setTranslateLang] = useState('Spanish');

  // Generate new story with images
  const generateStory = async () => {
    setLoading(true);
    try {
      const res = await axios.post('/api/stories', { text: prompt, num_pages: numPages });
      console.log('Pages:', res.data.pages);
      setStoryPages(res.data.pages);
      setPageIndex(0);
    } catch (e) {
      console.error('Generate error:', e);
      alert('Failed to generate story.');
    }
    setLoading(false);
  };

  // Translate story pages
  const translateStory = async () => {
    setLoading(true);
    try {
      const translated = await Promise.all(
        storyPages.map(async (page) => {
          const res = await axios.post('/api/translate', { text: page.text, target_lang: translateLang });
          return { ...page, translation: res.data.translation };
        })
      );
      setStoryPages(translated);
      setPageIndex(0);
    } catch (e) {
      console.error('Translate error:', e);
      alert('Translation failed.');
    }
    setLoading(false);
  };

  // Read Aloud using TTS endpoint
  const readAloud = async () => {
    if (!storyPages.length) return;
    setLoading(true);
    try {
      const text = storyPages[pageIndex].translation || storyPages[pageIndex].text;
      const res = await axios.post(
        '/api/tts',
        { text },
        { responseType: 'arraybuffer' }
      );
      const blob = new Blob([res.data], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (e) {
      console.error('TTS error:', e);
      alert('Failed to play speech.');
    }
    setLoading(false);
  };

  return (
    <div className="storybook-container">
      <h1 className="storybook-title">My AI Storybook</h1>

      <textarea
        className="storybook-textarea"
        placeholder="Enter your story prompt..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />

      <div className="controls">
        <label>
          Pages:
          <input
            type="number"
            min={1}
            max={10}
            value={numPages}
            onChange={(e) => setNumPages(Number(e.target.value))}
          />
        </label>
        <button onClick={generateStory} disabled={loading || !prompt.trim()}>
          {loading ? 'Generating…' : 'Generate Storybook'}
        </button>

        <label>
          Translate to:
          <select
            value={translateLang}
            onChange={(e) => setTranslateLang(e.target.value)}
          >
            <option>Spanish</option>
            <option>French</option>
            <option>German</option>
            <option>Chinese</option>
          </select>
        </label>
        <button
          onClick={translateStory}
          disabled={loading || storyPages.length === 0}
        >
          {loading ? 'Translating…' : 'Translate Story'}
        </button>

        <button
          onClick={readAloud}
          disabled={loading || storyPages.length === 0}
        >
          {loading ? 'Speaking…' : 'Read Aloud'}
        </button>
      </div>

      {storyPages.length > 0 && (
        <div className="flipbook">
          <button
            className="nav-button"
            onClick={() => setPageIndex((i) => Math.max(i - 1, 0))}
            disabled={pageIndex === 0}
          >
            ‹
          </button>

          <div className="page-frame">
            {storyPages[pageIndex].image_url ? (
              <img
                className="page-img"
                src={storyPages[pageIndex].image_url}
                alt={`Page ${pageIndex + 1}`}
              />
            ) : (
              <div className="no-image">Image not available</div>
            )}
            <div className="page-text">
              {storyPages[pageIndex].translation || storyPages[pageIndex].text}
            </div>
          </div>

          <button
            className="nav-button"
            onClick={() =>
              setPageIndex((i) => Math.min(i + 1, storyPages.length - 1))
            }
            disabled={pageIndex === storyPages.length - 1}
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
}

export default App;