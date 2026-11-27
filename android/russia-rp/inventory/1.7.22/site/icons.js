const iconPaths = {
 bag:'<path fill="currentColor" stroke="none" d="M7 5V4a3 3 0 0 1 3-3h4a3 3 0 0 1 3 3v1h1a3 3 0 0 1 3 3v5c-1.7 1.1-4.4 1.6-7 1.8v-2.1h-4v2.1C7.4 14.6 4.7 14 3 13V8a3 3 0 0 1 3-3zm2 0h6V4a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1zM4 15c1.8.9 3.9 1.4 6 1.5v1.7h4v-1.7c2.1-.1 4.2-.6 6-1.5v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/>',
 profile:'<circle cx="12" cy="8" r="4"/><path d="M3 21c.6-5 3.5-7.5 9-7.5s8.4 2.5 9 7.5"/>',
 stats:'<path d="M3 21h18"/><path fill="currentColor" stroke="none" d="M4 18v-6h4v6zm6 0V4h4v14zm6 0V8h4v10z"/>',
 finance:'<circle cx="12" cy="12" r="9"/><path d="M9 17V7h4a3 3 0 1 1 0 6H8m0 2h5"/>',
 image:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.2" cy="8" r="1.2"/><path d="m4 17 5-5 3 3 4-6 4 7"/>',
 award:'<path d="m8 14-3 7 4-1 2 2 2-7m3-1 3 7-4-1-2 2"/><circle cx="12" cy="9" r="7"/><path fill="currentColor" stroke="none" d="m12 4 1.3 2.8 3 .4-2.2 2.2.5 3.1-2.6-1.4-2.6 1.4.5-3.1-2.2-2.2 3-.4z"/>',
 food:'<path d="M4 2v7c0 3 6 3 6 0V2M7 2v20m12 0V2c-4 3-5 10-1 11h1"/>',
 close:'<path d="m4 4 16 16M20 4 4 20"/>',plus:'<path stroke-width="3" d="M12 4v16M4 12h16"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2" fill="currentColor" stroke="none"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/><path d="M12 14v3" stroke="#342c26"/>',
 longarm:'<path d="m2 16 5-3 3-4h8l2-2 2 1-4 5h-6l-2 4-2-1 1-3-5 6z"/>',
 sidearm:'<path d="M3 7h17v5h-9l-2 7-5-1 3-7H3z"/>',
 blade:'<path d="m4 20 5-6 2 2-5 6zm6-7L21 2c0 5-3 10-8 13zm-2-1 5 5"/>',
 glasses:'<path d="M2 10c2-2 5-2 8-1l2 1 2-1c3-1 6-1 8 1l-2 6c-3 2-6 0-6-3v-1h-4v1c0 3-3 5-6 3z"/>', coat:'<path d="m3 7 5-4 4 3 4-3 5 4-2 6-3-2v10H8V11l-3 2z"/>'
};
function icon(name){const el=document.createElementNS('http://www.w3.org/2000/svg','svg');el.setAttribute('class','icon');el.setAttribute('viewBox','0 0 24 24');el.setAttribute('aria-hidden','true');el.innerHTML=iconPaths[name];return el}
document.querySelectorAll('[data-icon]').forEach(el=>el.append(icon(el.dataset.icon)));
