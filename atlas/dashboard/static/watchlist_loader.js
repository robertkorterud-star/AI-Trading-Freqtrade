(function(){
  function load(){
    if(!location.pathname.startsWith('/analysis')) return;
    var s=document.createElement('script'); s.src='/static/watchlist_ui.js'; s.defer=true; document.head.appendChild(s);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',load); else load();
})();
