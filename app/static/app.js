// GADS preview — JS plano, sin frameworks.
// Maneja login con JWT en localStorage, fetches autenticados al backend,
// y renderiza listas/tablas. Si el backend devuelve 401, limpia el token y
// regresa al login. Todas las respuestas se muestran en el panel "Respuesta API".

const GADS = (() => {
  const TOKEN_KEY = "gads_jwt";
  const USER_KEY = "gads_user";

  // ---- token storage ----
  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }
  function setToken(t) {
    localStorage.setItem(TOKEN_KEY, t);
  }
  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function setUser(u) {
    localStorage.setItem(USER_KEY, JSON.stringify(u));
  }
  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  }

  // ---- fetch wrapper ----
  async function apiFetch(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(path, { ...options, headers });
    const meta = { method: options.method || "GET", path, status: res.status };

    let data;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json().catch(() => null);
    } else {
      data = await res.text().catch(() => "");
    }

    // panel
    showApiResponse(meta, data);

    if (res.status === 401 && !path.endsWith("/auth/login")) {
      clearAuth();
      toast("Sesión expirada. Volvé a ingresar.", "error");
      setTimeout(() => (window.location.href = "./index.html"), 600);
    }

    if (!res.ok) {
      const err = new Error(
        (data && (data.detail || data.message)) || `HTTP ${res.status}`
      );
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  // ---- UI helpers ----
  function showApiResponse(meta, data) {
    const panelMeta = document.getElementById("api-meta");
    const panelBody = document.getElementById("api-response");
    if (!panelBody) return;
    if (panelMeta) {
      const okClass =
        meta.status >= 200 && meta.status < 300 ? "" : meta.status >= 400 ? "error" : "";
      panelMeta.innerHTML = `<span class="${okClass}">${meta.method} ${meta.path} → <strong>${meta.status}</strong></span>`;
    }
    const text =
      typeof data === "string" ? data : JSON.stringify(data, null, 2) || "(sin body)";
    panelBody.textContent = text;
  }

  function toast(msg, kind = "info") {
    const el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.className = `toast ${kind}`;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (el.hidden = true), 3500);
  }

  function formToObject(form) {
    const fd = new FormData(form);
    const obj = {};
    for (const [k, v] of fd.entries()) {
      if (v === "" || v === null) continue;
      obj[k] = v;
    }
    return obj;
  }

  function showError(target, err) {
    const msg = err.data && err.data.detail
      ? typeof err.data.detail === "string"
        ? err.data.detail
        : JSON.stringify(err.data.detail)
      : err.message;
    if (target) {
      target.textContent = msg;
      target.className = "message error";
      target.hidden = false;
    }
    toast(`Error ${err.status || ""}: ${msg}`.trim(), "error");
  }

  // ---- LOGIN page ----
  function initLoginPage() {
    // Si ya hay token, ir directo al dashboard.
    if (getToken()) {
      window.location.href = "./dashboard.html";
      return;
    }

    const form = document.getElementById("login-form");
    const msg = document.getElementById("login-message");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      msg.hidden = true;
      const payload = formToObject(form);

      try {
        const data = await apiFetch("/auth/login", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setToken(data.access_token);

        // Cargamos /auth/me para mostrar usuario en dashboard.
        const me = await apiFetch("/auth/me");
        setUser(me);

        window.location.href = "./dashboard.html";
      } catch (err) {
        showError(msg, err);
      }
    });
  }

  // ---- DASHBOARD ----
  async function initDashboard() {
    if (!getToken()) {
      window.location.href = "./index.html";
      return;
    }

    // Header usuario.
    const userLabel = document.getElementById("user-label");
    const cached = getUser();
    if (cached) {
      userLabel.textContent = `${cached.nombre_usuario} · ${cached.rol}`;
    }
    // Revalidar /auth/me en background.
    apiFetch("/auth/me")
      .then((me) => {
        setUser(me);
        userLabel.textContent = `${me.nombre_usuario} · ${me.rol}`;
      })
      .catch(() => { /* el wrapper ya maneja 401 */ });

    // Logout.
    document.getElementById("logout-btn").addEventListener("click", () => {
      clearAuth();
      window.location.href = "./index.html";
    });

    // Nav.
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });

    // Dashboards.
    document.getElementById("dashboards-refresh").addEventListener("click", loadDashboards);
    document.getElementById("dash-estado").addEventListener("change", loadEmpleadosStatus);
    document.getElementById("dash-id-empresa").addEventListener("change", loadDashboards);

    // Empresas.
    document.getElementById("empresas-refresh").addEventListener("click", loadEmpresas);
    document.getElementById("empresas-export").addEventListener("click", () =>
      downloadCsv("/empresas/export", "empresas.csv")
    );
    document.getElementById("empresa-form").addEventListener("submit", onCrearEmpresa);
    wireBulkImport("empresas", "/empresas/import", loadEmpresas);

    // Empleados.
    document.getElementById("empleados-refresh").addEventListener("click", loadEmpleados);
    document.getElementById("empleados-export").addEventListener("click", () =>
      downloadCsv("/empleados/export", "empleados.csv")
    );
    document.getElementById("empleado-form").addEventListener("submit", onCrearEmpleado);
    wireBulkImport("empleados", "/empleados/import", loadEmpleados);

    // Usuarios.
    document.getElementById("usuarios-refresh").addEventListener("click", loadUsuarios);
    document.getElementById("usuarios-export").addEventListener("click", () =>
      downloadCsv("/usuarios/export", "usuarios.csv")
    );
    document.getElementById("usuario-form").addEventListener("submit", onCrearUsuario);
    wireBulkImport("usuarios", "/usuarios/import", loadUsuarios);

    // Fichadas.
    document.getElementById("fichadas-refresh").addEventListener("click", loadFichadas);
    document.getElementById("fichadas-export").addEventListener("click", () =>
      downloadBlob("/fichadas/export", "fichadas.xlsx")
    );
    document.getElementById("fichada-form").addEventListener("submit", onCrearFichada);
    document.getElementById("fichadas-import-form").addEventListener("submit", onImportFichadas);

    // Default view: dashboards.
    loadDashboards();
  }

  function switchView(name) {
    document.querySelectorAll(".nav-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.view === name);
    });
    document.querySelectorAll(".view").forEach((v) => {
      v.classList.toggle("active", v.id === `view-${name}`);
    });
    // Auto-load on switch.
    if (name === "dashboards") loadDashboards();
    if (name === "empresas") loadEmpresas();
    if (name === "empleados") loadEmpleados();
    if (name === "usuarios") loadUsuarios();
    if (name === "fichadas") loadFichadas();
  }

  // ---- EMPRESAS ----
  async function loadEmpresas() {
    const tbody = document.querySelector("#empresas-table tbody");
    tbody.innerHTML = `<tr><td colspan="5" class="empty">Cargando…</td></tr>`;
    try {
      const rows = await apiFetch("/empresas");
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty">Sin empresas todavía.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows
        .map(
          (r) => `<tr>
            <td>${r.id_empresa}</td>
            <td>${escapeHtml(r.razon_social)}</td>
            <td>${escapeHtml(r.cuit)}</td>
            <td>${escapeHtml(r.email_contacto)}</td>
            <td>${escapeHtml(r.estado)}</td>
          </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function onCrearEmpresa(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const body = formToObject(form);
    try {
      await apiFetch("/empresas", { method: "POST", body: JSON.stringify(body) });
      toast("Empresa creada", "success");
      form.reset();
      loadEmpresas();
    } catch (err) {
      showError(null, err);
    }
  }

  // ---- EMPLEADOS ----
  async function loadEmpleados() {
    const tbody = document.querySelector("#empleados-table tbody");
    tbody.innerHTML = `<tr><td colspan="8" class="empty">Cargando…</td></tr>`;
    try {
      const rows = await apiFetch("/empleados");
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin empleados todavía.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows
        .map(
          (r) => `<tr>
            <td>${r.id_empleado}</td>
            <td>${r.id_empresa}</td>
            <td>${escapeHtml(r.legajo)}</td>
            <td>${escapeHtml(r.nombre)}</td>
            <td>${escapeHtml(r.apellido)}</td>
            <td>${escapeHtml(r.dni)}</td>
            <td>${escapeHtml(r.tipo_jornada)}</td>
            <td>${escapeHtml(r.estado)}</td>
          </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function onCrearEmpleado(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const body = formToObject(form);
    // Casteos numéricos.
    if (body.id_empresa) body.id_empresa = parseInt(body.id_empresa, 10);
    try {
      await apiFetch("/empleados", { method: "POST", body: JSON.stringify(body) });
      toast("Empleado creado", "success");
      form.reset();
      loadEmpleados();
    } catch (err) {
      showError(null, err);
    }
  }

  // ---- USUARIOS ----
  async function loadUsuarios() {
    const tbody = document.querySelector("#usuarios-table tbody");
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Cargando…</td></tr>`;
    try {
      const rows = await apiFetch("/usuarios");
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">Sin usuarios todavía.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows
        .map(
          (r) => `<tr>
            <td>${r.id_usuario}</td>
            <td>${escapeHtml(r.nombre_usuario)}</td>
            <td>${escapeHtml(r.email)}</td>
            <td>${escapeHtml(r.rol)}</td>
            <td>${r.id_empleado}</td>
            <td>${escapeHtml(r.estado)}</td>
            <td>${escapeHtml(r.ultimo_acceso || "—")}</td>
          </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function onCrearUsuario(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const body = formToObject(form);
    if (body.id_empleado) body.id_empleado = parseInt(body.id_empleado, 10);
    try {
      await apiFetch("/usuarios", { method: "POST", body: JSON.stringify(body) });
      toast("Usuario creado", "success");
      form.reset();
      loadUsuarios();
    } catch (err) {
      showError(null, err);
    }
  }

  // ---- FICHADAS ----
  async function loadFichadas() {
    const tbody = document.querySelector("#fichadas-table tbody");
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Cargando…</td></tr>`;
    try {
      const rows = await apiFetch("/fichadas");
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">Sin fichadas todavía.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows
        .map(
          (r) => `<tr>
            <td>${r.id_fichada}</td>
            <td>${escapeHtml(r.fecha_hora)}</td>
            <td>${escapeHtml(r.tipo_fichada)}</td>
            <td>${r.id_empleado}</td>
            <td>${r.id_origen_fichada}</td>
            <td>${r.fue_corregida ? "sí" : "no"}</td>
            <td>${escapeHtml(r.observacion || "")}</td>
          </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function onCrearFichada(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const body = formToObject(form);
    if (body.id_empleado) body.id_empleado = parseInt(body.id_empleado, 10);
    if (body.id_origen_fichada) body.id_origen_fichada = parseInt(body.id_origen_fichada, 10);
    // datetime-local viene sin TZ — el backend acepta naive ISO.
    try {
      await apiFetch("/fichadas", { method: "POST", body: JSON.stringify(body) });
      toast("Fichada creada", "success");
      form.reset();
      loadFichadas();
    } catch (err) {
      showError(null, err);
    }
  }

  // ---- FICHADAS IMPORT (planilla CSV) ----
  async function onImportFichadas(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const file = fd.get("file");
    const idEmpresa = fd.get("id_empresa");
    const dryRun = fd.get("dry_run") === "on";

    if (!file || !file.name) {
      toast("Seleccioná un CSV", "error");
      return;
    }

    const body = new FormData();
    body.append("file", file);

    const qs = new URLSearchParams();
    qs.set("dry_run", String(dryRun));
    if (idEmpresa) qs.set("id_empresa", String(idEmpresa));

    const path = `/fichadas/import?${qs.toString()}`;
    try {
      const data = await apiFetch(path, { method: "POST", body });
      renderResumen(data);
      toast(
        `Importadas ${data.fichadas_creadas} fichadas y ${data.novedades_creadas} novedades`,
        "success"
      );
      loadFichadas();
    } catch (err) {
      const panel = document.getElementById("fichadas-resumen");
      panel.hidden = false;
      if (err.data) renderResumen(err.data, true);
      showError(null, err);
    }
  }

  // Genérico: botón "Importar CSV" para empresas/empleados/usuarios.
  function wireBulkImport(prefix, endpoint, reloadFn) {
    const btn = document.getElementById(`${prefix}-import`);
    const input = document.getElementById(`${prefix}-import-file`);
    if (!btn || !input) return;
    btn.addEventListener("click", () => input.click());
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      const body = new FormData();
      body.append("file", file);
      try {
        const data = await apiFetch(endpoint, { method: "POST", body });
        const creados = data.creados ?? 0;
        const omitidos = data.omitidos ?? 0;
        const errores = Array.isArray(data.errores) ? data.errores.length : 0;
        const kind = errores > 0 ? "info" : "success";
        toast(
          `Importados ${creados} · omitidos ${omitidos} · errores ${errores}`,
          kind
        );
        if (errores > 0) {
          console.warn(`${prefix} import errores:`, data.errores);
        }
        if (reloadFn) reloadFn();
      } catch (err) {
        showError(null, err);
      } finally {
        input.value = "";
      }
    });
  }

  function renderResumen(data, isError = false) {
    const panel = document.getElementById("fichadas-resumen");
    panel.hidden = false;
    document.getElementById("res-total").textContent = data.total_filas ?? "?";
    document.getElementById("res-creadas").textContent = data.fichadas_creadas ?? "?";
    document.getElementById("res-novedades").textContent = data.novedades_creadas ?? "?";
    const errCount = Array.isArray(data.errores) ? data.errores.length : 0;
    document.getElementById("res-errores").textContent = errCount;

    const errBox = document.getElementById("fichadas-errores");
    if (errCount > 0) {
      errBox.textContent = data.errores
        .slice(0, 50)
        .map((e) => `fila ${e.fila ?? "?"}: ${e.mensaje ?? JSON.stringify(e)}`)
        .join("\n");
      if (errCount > 50) errBox.textContent += `\n… (${errCount - 50} errores más)`;
    } else {
      errBox.textContent = "";
    }
  }

  // ---- File download (CSV / XLSX) ----
  async function downloadBlob(path, filename) {
    const token = getToken();
    if (!token) {
      toast("Sin sesión", "error");
      return;
    }
    try {
      const res = await fetch(path, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        clearAuth();
        window.location.href = "./index.html";
        return;
      }
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        showApiResponse(
          { method: "GET", path, status: res.status },
          text || `HTTP ${res.status}`
        );
        toast(`Error ${res.status} al exportar`, "error");
        return;
      }
      const blob = await res.blob();
      showApiResponse(
        { method: "GET", path, status: res.status },
        `(archivo descargado, ${blob.size} bytes — ${filename})`
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast(`Descargado ${filename}`, "success");
    } catch (err) {
      toast(`Error: ${err.message}`, "error");
    }
  }
  const downloadCsv = downloadBlob;  // alias retrocompatible

  // ---- DASHBOARDS ----
  function _idEmpresaFiltro() {
    const v = document.getElementById("dash-id-empresa").value.trim();
    return v ? parseInt(v, 10) : null;
  }

  async function loadDashboards() {
    await loadResumen();
    await loadEmpleadosStatus();
  }

  async function loadResumen() {
    const id = _idEmpresaFiltro();
    const qs = id ? `?id_empresa=${id}` : "";
    try {
      const data = await apiFetch(`/dashboards/resumen${qs}`);
      document.getElementById("dash-empresas-total").textContent = data.empresas?.total ?? "—";
      document.getElementById("dash-empleados-total").textContent = data.empleados?.total ?? "—";
      document.getElementById("dash-empleados-activos").textContent = data.empleados?.activos ?? "—";
      document.getElementById("dash-usuarios-total").textContent = data.usuarios?.total ?? "—";
      document.getElementById("dash-fichadas-total").textContent = data.fichadas?.total ?? "—";
      document.getElementById("dash-fichadas-7d").textContent = data.fichadas?.ultimos_7_dias ?? "—";
      document.getElementById("dash-novedades-pend").textContent = data.novedades?.pendientes ?? "—";
      document.getElementById("dash-novedades-total").textContent = data.novedades?.total ?? "—";
      _renderKvList("dash-cat-list", data.empleados_por_categoria);
      _renderKvList("dash-jor-list", data.empleados_por_jornada);
      _renderKvList("dash-rol-list", data.usuarios?.por_rol);
    } catch (err) {
      toast(`Resumen: ${err.message}`, "error");
    }
  }

  async function loadEmpleadosStatus() {
    const tbody = document.querySelector("#dashboards-empleados-table tbody");
    tbody.innerHTML = `<tr><td colspan="10" class="empty">Cargando…</td></tr>`;
    const id = _idEmpresaFiltro();
    const estado = document.getElementById("dash-estado").value;
    const qs = new URLSearchParams();
    if (id) qs.set("id_empresa", String(id));
    if (estado) qs.set("estado", estado);
    const path = `/dashboards/empleados/status${qs.toString() ? "?" + qs.toString() : ""}`;
    try {
      const data = await apiFetch(path);
      if (!data.items?.length) {
        tbody.innerHTML = `<tr><td colspan="10" class="empty">Sin empleados.</td></tr>`;
        return;
      }
      tbody.innerHTML = data.items
        .map(
          (i) => `<tr>
            <td>${i.id_empleado}</td>
            <td>${i.id_empresa}</td>
            <td>${escapeHtml(i.legajo)}</td>
            <td>${escapeHtml(i.nombre)} ${escapeHtml(i.apellido)}</td>
            <td>${escapeHtml(i.estado)}</td>
            <td>${escapeHtml(i.tipo_jornada)}</td>
            <td>${escapeHtml(i.ultima_fichada || "—")}</td>
            <td>${i.fichadas_ultimos_30_dias}</td>
            <td>${i.novedades_pendientes}</td>
            <td><button class="btn btn-ghost btn-small" data-detalle="${i.id_empleado}">Detalle</button></td>
          </tr>`
        )
        .join("");
      tbody.querySelectorAll("[data-detalle]").forEach((b) => {
        b.addEventListener("click", () => loadDetalleEmpleado(parseInt(b.dataset.detalle, 10)));
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" class="empty">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function loadDetalleEmpleado(id) {
    try {
      const d = await apiFetch(`/dashboards/empleados/${id}`);
      document.getElementById("dash-detalle-card").hidden = false;
      document.getElementById("dash-detalle-titulo").textContent =
        `Detalle — ${d.nombre} ${d.apellido} (legajo ${d.legajo})`;
      document.getElementById("det-fichadas-total").textContent = d.fichadas_total;
      document.getElementById("det-fichadas-30d").textContent = d.fichadas_ultimos_30_dias;
      document.getElementById("det-novedades-total").textContent = d.novedades_total;
      document.getElementById("det-novedades-pend").textContent = d.novedades_pendientes;
      _renderKvList("det-mes-list", d.fichadas_por_mes);
      _renderKvList("det-tipo-list", d.novedades_por_tipo);
      const partes = [
        `Empresa #${d.id_empresa}`,
        `Estado: ${d.estado}`,
        `Jornada: ${d.tipo_jornada}`,
        `Categoría: ${d.categoria_laboral}`,
      ];
      if (d.ultima_fichada) partes.push(`Última fichada: ${d.ultima_fichada}`);
      if (d.primera_fichada) partes.push(`Primera fichada: ${d.primera_fichada}`);
      document.getElementById("det-meta").textContent = partes.join(" · ");
      document.getElementById("dash-detalle-card").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      toast(`Detalle: ${err.message}`, "error");
    }
  }

  function _renderKvList(id, dict) {
    const ul = document.getElementById(id);
    if (!ul) return;
    if (!dict || Object.keys(dict).length === 0) {
      ul.innerHTML = `<li class="muted">— sin datos —</li>`;
      return;
    }
    ul.innerHTML = Object.entries(dict)
      .map(([k, v]) => `<li><span>${escapeHtml(k)}</span><span class="kv-val">${v}</span></li>`)
      .join("");
  }

  // ---- util ----
  function escapeHtml(v) {
    if (v === null || v === undefined) return "";
    return String(v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  return { initLoginPage, initDashboard };
})();
