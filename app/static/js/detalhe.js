document.addEventListener('DOMContentLoaded', function () {

  /* ── Timer ──────────────────────────────────────── */
  (function () {
    var totalSeg = window.SEG_REST || 0;
    var restantes = totalSeg;
    var label = document.getElementById('timerLabel');
    var bar = document.getElementById('timerProgress');
    var wrap = document.getElementById('timerBar');
    if (!label) return;

    function pad(n) { return n < 10 ? '0' + n : n; }

    function fmt(s) {
      var m = Math.floor(s / 60);
      var ss = s % 60;
      return m + 'min ' + pad(ss) + 's';
    }

    function tick() {
      if (restantes <= 0) {
        label.textContent = 'Sessão expirada — a redirecionar…';
        if (wrap) { wrap.className = 'timer-bar expirado'; }
        if (bar) { bar.style.width = '0%'; }
        setTimeout(function () { window.location.reload(); }, 1500);
        return;
      }

      var pct = Math.round((restantes / totalSeg) * 100);
      label.textContent = 'Sessão activa — ' + fmt(restantes);

      if (bar) { bar.style.width = pct + '%'; }
      if (wrap) {
        wrap.className = 'timer-bar';
        if (restantes < 60) { wrap.classList.add('critico'); }
        else if (restantes < 300) { wrap.classList.add('aviso'); }
      }

      restantes--;
      setTimeout(tick, 1000);
    }

    tick();

    /* Sincronizar com servidor a cada 30s */
    if (window.ESTADO_URL) {
      setInterval(function () {
        fetch(window.ESTADO_URL)
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.estado === 'bloqueado') {
              window.location.reload();
            } else if (d.segundos_restantes) {
              restantes = Math.min(restantes, d.segundos_restantes);
            }
          })
          .catch(function () {});
      }, 30000);
    }
  })();

  /* ── Qr Tabs ────────────────────────────────────── */
  document.querySelectorAll('.qr-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.qr-tab').forEach(function (t) { t.classList.remove('active'); });
      this.classList.add('active');
      var nome = this.dataset.tab;
      var wifi = document.getElementById('tabWifi');
      var pag = document.getElementById('tabPagina');
      if (wifi) { wifi.style.display = nome === 'wifi' ? '' : 'none'; }
      if (pag) { pag.style.display = nome === 'pagina' ? '' : 'none'; }
    });
  });

  /* ── Copiar ──────────────────────────────────────── */
  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = this.dataset.copy;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () {
          showToast('Copiado!', 'ok');
        });
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copiado!', 'ok');
      }
    });
  });

  /* ── Mostrar / esconder senha ────────────────────── */
  (function () {
    var btn = document.getElementById('eyeBtn');
    var dots = document.querySelector('.dots');
    var real = document.querySelector('.cred-val .real');
    var showIcon = btn ? btn.querySelector('.eye-show') : null;
    var hideIcon = btn ? btn.querySelector('.eye-hide') : null;
    var visible = false;

    if (!btn || !dots || !real) return;

    btn.addEventListener('click', function () {
      visible = !visible;
      dots.style.display = visible ? 'none' : 'inline';
      real.style.display = visible ? 'inline' : 'none';
      if (showIcon) showIcon.style.display = visible ? 'none' : 'block';
      if (hideIcon) hideIcon.style.display = visible ? 'block' : 'none';
    });
  })();

  /* ── Partilhar ───────────────────────────────────── */
  (function () {
    var btn = document.getElementById('shareBtn');
    if (!btn) return;

    btn.addEventListener('click', function () {
      if (navigator.share) {
        navigator.share({
          title: window.REDE_NOME || '',
          text: 'Rede: ' + (window.REDE_SSID || '') + '\nSenha: ' + (window.REDE_SENHA || ''),
          url: window.location.href
        }).catch(function () {});
      } else {
        var text = 'WiFi: ' + (window.REDE_SSID || '') + ' | Senha: ' + (window.REDE_SENHA || '');
        if (navigator.clipboard) {
          navigator.clipboard.writeText(text).then(function () {
            showToast('Dados copiados para partilha!', 'ok');
          });
        }
      }
    });
  })();

});
