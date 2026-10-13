const { app, BrowserWindow } = require('electron')
const http = require('node:http')
const fs = require('node:fs')
const path = require('node:path')

function startPackagedServer() {
  const root = path.join(__dirname, '..', 'dist')
  const mimeTypes = { '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' }
  const server = http.createServer((request, response) => {
    const requestedPath = request.url === '/' ? '/index.html' : request.url.split('?')[0]
    const filePath = path.resolve(root, `.${requestedPath}`)
    if (!filePath.startsWith(root) || !fs.existsSync(filePath)) {
      response.writeHead(404)
      response.end('Not found')
      return
    }
    response.writeHead(200, { 'Content-Type': mimeTypes[path.extname(filePath)] || 'text/html' })
    fs.createReadStream(filePath).pipe(response)
  })
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)))
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: '#f4f6fa',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (app.isPackaged) {
    const server = await startPackagedServer()
    window.on('closed', () => server.close())
    window.loadURL(`http://localhost:${server.address().port}`)
  } else {
    window.loadURL('http://127.0.0.1:5173')
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
