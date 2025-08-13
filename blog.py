import http.server
import socketserver
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

PORT = 8000
BLOG_FILE = "blogs.json"

# Ensure file exists
if not os.path.exists(BLOG_FILE):
    with open(BLOG_FILE, "w") as f:
        json.dump([], f)

def load_blogs():
    with open(BLOG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_blogs(blogs):
    with open(BLOG_FILE, "w") as f:
        json.dump(blogs, f, indent=2)

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>My Personal Blog</title>
  <style>
    body{font-family:Arial;margin:20px;background:#f7f7f7}
    h1{text-align:center}
    .container{max-width:900px;margin:0 auto}
    .blog-form, .posts{background:#fff;padding:15px;border-radius:8px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,0.06)}
    input, textarea{width:100%;padding:10px;margin:6px 0;border:1px solid #ddd;border-radius:4px}
    .btn{display:inline-block;padding:8px 12px;border:none;border-radius:5px;cursor:pointer}
    .btn-primary{background:#007bff;color:#fff}
    .btn-warning{background:#ffc107;color:#000}
    .btn-danger{background:#dc3545;color:#fff}
    .post{border-bottom:1px solid #eee;padding:10px 0}
    .meta{color:#666;font-size:13px}
    .actions{margin-top:8px}
  </style>
</head>
<body>
  <div class="container">
    <h1>📓 My Personal Blog</h1>

    <div class="blog-form">
      <h2 id="form-title">Create a New Post</h2>
      <input type="hidden" id="postId" value="">
      <input id="title" placeholder="Post title">
      <textarea id="content" rows="6" placeholder="Write your content..."></textarea>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-primary" onclick="savePost()">Save Post</button>
        <button class="btn" onclick="resetForm()">Clear</button>
      </div>
    </div>

    <div class="posts">
      <h2>All Posts</h2>
      <div id="postsList">Loading…</div>
    </div>
  </div>

<script>
async function loadPosts(){
  const res = await fetch('/get');
  const posts = await res.json();
  const container = document.getElementById('postsList');
  if(!posts.length){ container.innerHTML = '<p>No posts yet.</p>'; return; }
  // show newest first
  posts.sort((a,b)=> b.id - a.id);
  container.innerHTML = posts.map(p => `
    <div class="post">
      <h3>${escapeHtml(p.title)}</h3>
      <div class="meta">${p.date}</div>
      <p>${escapeHtml(p.content).replace(/\\n/g, '<br>')}</p>
      <div class="actions">
        <button class="btn btn-warning" onclick="editPost(${p.id})">Edit</button>
        <button class="btn btn-danger" onclick="deletePost(${p.id})">Delete</button>
      </div>
    </div>
  `).join('');
}

function escapeHtml(unsafe){
  return unsafe
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#039;');
}

function resetForm(){
  document.getElementById('postId').value = '';
  document.getElementById('title').value = '';
  document.getElementById('content').value = '';
  document.getElementById('form-title').innerText = 'Create a New Post';
}

async function savePost(){
  const id = document.getElementById('postId').value;
  const title = document.getElementById('title').value.trim();
  const content = document.getElementById('content').value.trim();
  if(!title || !content){ alert('Please enter title and content'); return; }

  const payload = { title, content };
  if(id) payload.id = Number(id);

  const res = await fetch('/save', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(res.ok){
    resetForm();
    loadPosts();
  } else {
    alert('Error saving post');
  }
}

async function editPost(id){
  const res = await fetch('/get');
  const posts = await res.json();
  const p = posts.find(x=> x.id === id);
  if(!p){ alert('Post not found'); return; }
  document.getElementById('postId').value = p.id;
  document.getElementById('title').value = p.title;
  document.getElementById('content').value = p.content;
  document.getElementById('form-title').innerText = 'Edit Post (ID: ' + p.id + ')';
  window.scrollTo({top:0, behavior:'smooth'});
}

async function deletePost(id){
  if(!confirm('Delete this post?')) return;
  const res = await fetch('/delete', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id })
  });
  if(res.ok) loadPosts();
  else alert('Delete failed');
}

window.onload = loadPosts;
</script>
</body>
</html>
"""

class BlogHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return
        if self.path == '/get':
            blogs = load_blogs()
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(blogs).encode('utf-8'))
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length)
            try:
                payload = json.loads(data.decode('utf-8'))
            except:
                self.send_response(400); self.end_headers(); return
            blogs = load_blogs()
            # update if id provided
            if 'id' in payload and payload['id'] is not None:
                updated = False
                for i,b in enumerate(blogs):
                    if b.get('id') == payload['id']:
                        blogs[i]['title'] = payload['title']
                        blogs[i]['content'] = payload['content']
                        blogs[i]['date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        updated = True
                        break
                if not updated:
                    # if id not found, append as new
                    new_id = max([b.get('id',0) for b in blogs], default=0) + 1
                    blogs.append({'id': new_id, 'title': payload['title'], 'content': payload['content'], 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
            else:
                # create new ID
                new_id = max([b.get('id',0) for b in blogs], default=0) + 1
                blogs.append({'id': new_id, 'title': payload['title'], 'content': payload['content'], 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
            save_blogs(blogs)
            self.send_response(200); self.end_headers()
            return

        if self.path == '/delete':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length)
            try:
                payload = json.loads(data.decode('utf-8'))
                del_id = payload.get('id')
            except:
                self.send_response(400); self.end_headers(); return
            blogs = load_blogs()
            blogs = [b for b in blogs if b.get('id') != del_id]
            save_blogs(blogs)
            self.send_response(200); self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(('', PORT), BlogHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
