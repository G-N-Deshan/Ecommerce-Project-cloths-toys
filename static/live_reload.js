/* Real-time site update polling
   Detects admin changes and auto-reloads the page. */
(function () {
    if (!window.fetch) return;
    var lastTs = '', timer, INTERVAL = 8000;

    function poll() {
        fetch('/check-updates/')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (lastTs && d.ts && d.ts !== lastTs) location.reload();
                if (d.ts) lastTs = d.ts;
            })
            .catch(function () {});
    }
    function start() { if (!timer) { timer = setInterval(poll, INTERVAL); poll(); } }
    function stop() { clearInterval(timer); timer = null; }

    document.addEventListener('visibilitychange', function () {
        document.hidden ? stop() : start();
    });
    if (!document.hidden) start();
})();
