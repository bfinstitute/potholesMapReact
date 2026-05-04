const { createProxyMiddleware } = require('http-proxy-middleware');

const backendProxy = createProxyMiddleware({
  target: 'http://127.0.0.1:5005',
  changeOrigin: true,
  timeout: 120000,
  proxyTimeout: 120000,
  onError(err, req, res) {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Backend unavailable: ' + err.message }));
  },
});

module.exports = function(app) {
  app.use('/api', backendProxy);
  app.use('/cache', backendProxy);
  app.post('/chat', backendProxy);
};
