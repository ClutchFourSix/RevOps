import express from 'express';
import fetch from 'node-fetch';
import * as cheerio from 'cheerio';

const app = express();
app.use(express.static('public'));

app.get('/api/search', async (req, res) => {
  const { city, state } = req.query;

  const query = `managed IT services in ${city} ${state}`;
  const url = `https://www.bing.com/search?q=${encodeURIComponent(query)}`;

  try {
    const response = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });

    const html = await response.text();
    const $ = cheerio.load(html);

    const results = [];

    $('li.b_algo').each((i, el) => {
      const name = $(el).find('h2').text();
      const link = $(el).find('a').attr('href');

      if (name && link) {
        results.push({ name, website: link });
      }
    });

    res.json(results);

  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch data' });
  }
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));
