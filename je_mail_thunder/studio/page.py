"""
The page of MailThunder Studio: its HTML, its style and its script, kept as text so the package ships no
data files. The script only ever writes text into the page (``textContent``), never markup, so a subject or
a sender that arrived by mail cannot run in the browser.
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MailThunder Studio</title>
<link rel="stylesheet" href="/studio.css">
</head>
<body>
<header>
  <h1>MailThunder Studio</h1>
  <button id="language" type="button">中文</button>
</header>
<nav id="navigation"></nav>
<main id="view"></main>
<script src="/studio.js"></script>
</body>
</html>
"""

STUDIO_CSS = r"""
:root { --ink: #1c2430; --muted: #5b6676; --line: #d5dbe3; --paper: #ffffff; --ground: #f3f5f8;
        --accent: #1d5fd0; --good: #1b7a43; --warn: #a15c00; --bad: #b3261e; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e6eaf0; --muted: #9aa5b4; --line: #344052; --paper: #1b222c; --ground: #12171e;
          --accent: #7fb0ff; --good: #5fd08a; --warn: #f0b35a; --bad: #ff8a80; }
}
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.5 system-ui, "Segoe UI", "Noto Sans TC", sans-serif; color: var(--ink);
       background: var(--ground); }
header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px;
         background: var(--paper); border-bottom: 1px solid var(--line); }
h1 { font-size: 18px; margin: 0; }
h2 { font-size: 16px; margin: 0 0 8px; }
nav { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 16px; background: var(--paper);
      border-bottom: 1px solid var(--line); }
nav button, header button, main button { font: inherit; color: var(--ink); background: var(--ground);
      border: 1px solid var(--line); border-radius: 6px; padding: 6px 12px; cursor: pointer; }
nav button.current { color: var(--paper); background: var(--accent); border-color: var(--accent); }
main { max-width: 1100px; margin: 0 auto; padding: 16px; }
section { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px;
          margin-bottom: 14px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: 5px 10px 5px 0; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; white-space: nowrap; }
pre { margin: 0; padding: 10px; background: var(--ground); border-radius: 6px; white-space: pre-wrap;
      word-break: break-word; max-height: 420px; overflow: auto; font-size: 13px; }
label { display: block; color: var(--muted); margin: 8px 0 2px; }
input, textarea { width: 100%; font: inherit; color: var(--ink); background: var(--ground);
                  border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; }
textarea { min-height: 80px; font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
.row { display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
.muted { color: var(--muted); }
.healthy { color: var(--good); font-weight: 600; }
.degraded, .unknown { color: var(--warn); font-weight: 600; }
.down, .problem { color: var(--bad); font-weight: 600; }
"""

STUDIO_JS = r"""
(function () {
  "use strict";

  var TEXT = {
    en: {dashboard: "Dashboard", accounts: "Accounts", templates: "Templates", triggers: "Triggers",
         policies: "Policies", projects: "Projects", logs: "Logs", settings: "Settings",
         account: "Account", health: "Provider health", counts: "Overview", recent: "Recent activity",
         sendTest: "Send a mail", send: "Send", check: "Check the connection", servers: "Servers",
         providers: "Registered providers", directories: "Template directories", render: "Render",
         context: "Context (JSON)", events: "Events", subscriptions: "Handlers", backends: "Trigger backends",
         poll: "Look for new mail now", policy: "Attachment policy", save: "Save", layer: "Mail layer",
         log: "Log", audit: "Audit log", refresh: "Refresh", none: "Nothing yet.", working: "Working...",
         noToken: "This page was opened without its token. Use the address MailThunder Studio printed.",
         policyNote: "Empty lifts a limit. Lists are separated by commas. The change lasts while Studio runs.",
         sent: "Sent."},
    zh: {dashboard: "儀表板", accounts: "帳號", templates: "模板", triggers: "觸發器",
         policies: "政策", projects: "專案", logs: "日誌", settings: "設定",
         account: "帳號", health: "供應商健康狀態", counts: "總覽", recent: "最近活動",
         sendTest: "寄送郵件", send: "寄送", check: "檢查連線", servers: "伺服器",
         providers: "已註冊的供應商", directories: "模板目錄", render: "產生內容",
         context: "Context (JSON)", events: "事件", subscriptions: "處理函式", backends: "觸發器後端",
         poll: "立即查看新郵件", policy: "附件政策", save: "儲存", layer: "郵件層",
         log: "日誌", audit: "稽核日誌", refresh: "重新整理", none: "目前沒有資料。", working: "處理中...",
         noToken: "這個頁面開啟時沒有帶著權杖。請使用 MailThunder Studio 印出的網址。",
         policyNote: "留空表示不設限。清單以逗號分隔。變更只在 Studio 執行期間有效。",
         sent: "已寄出。"}
  };
  var PAGES = ["dashboard", "accounts", "templates", "triggers", "policies", "projects", "logs", "settings"];
  var language = localStorage.getItem("mail-thunder-language") || "en";
  var current = "dashboard";
  var token = new URLSearchParams(location.hash.slice(1)).get("token") ||
    sessionStorage.getItem("mail-thunder-token") || "";
  if (token) {
    sessionStorage.setItem("mail-thunder-token", token);
    history.replaceState(null, "", location.pathname);
  }

  function t(key) { return TEXT[language][key] || key; }

  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    if (className) { node.className = className; }
    return node;
  }

  function show(value) {
    if (value === null || value === undefined || value === "") { return "-"; }
    return typeof value === "object" ? JSON.stringify(value) : String(value);
  }

  function section(title) {
    var node = el("section");
    node.appendChild(el("h2", title));
    return node;
  }

  function keyValues(object) {
    var table = el("table");
    Object.keys(object || {}).forEach(function (key) {
      var row = el("tr");
      row.appendChild(el("th", key));
      row.appendChild(el("td", show(object[key]), key === "state" ? String(object[key]) : ""));
      table.appendChild(row);
    });
    return table;
  }

  function grid(rows) {
    if (!rows || !rows.length) { return el("p", t("none"), "muted"); }
    var columns = Object.keys(rows[0]);
    var table = el("table");
    var head = el("tr");
    columns.forEach(function (column) { head.appendChild(el("th", column)); });
    table.appendChild(head);
    rows.forEach(function (item) {
      var row = el("tr");
      columns.forEach(function (column) {
        row.appendChild(el("td", show(item[column]), column === "state" ? String(item[column]) : ""));
      });
      table.appendChild(row);
    });
    return table;
  }

  function api(method, path, body) {
    var options = {method: method, headers: {"X-MailThunder-Token": token}};
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) { throw new Error((data.error || response.status) + ": " + (data.message || "")); }
        return data;
      });
    });
  }

  function action(label, run, output) {
    var button = el("button", label);
    button.type = "button";
    button.addEventListener("click", function () {
      output.textContent = t("working");
      output.className = "muted";
      run().then(function (result) {
        output.className = "";
        output.textContent = typeof result === "string" ? result : JSON.stringify(result, null, 2);
      }).catch(function (error) {
        output.className = "problem";
        output.textContent = error.message;
      });
    });
    return button;
  }

  function field(parent, label, multiline) {
    parent.appendChild(el("label", label));
    var input = el(multiline ? "textarea" : "input");
    parent.appendChild(input);
    return input;
  }

  var views = {
    dashboard: function (view) {
      return api("GET", "/api/dashboard").then(function (data) {
        var account = section(t("account"));
        account.appendChild(keyValues(data.account));
        var health = section(t("health"));
        health.appendChild(grid(data.health));
        var counts = section(t("counts"));
        data.counts.version = data.version;
        counts.appendChild(keyValues(data.counts));
        var compose = section(t("sendTest"));
        var to = field(compose, "to");
        var subject = field(compose, "subject");
        var text = field(compose, "text", true);
        var output = el("pre");
        var row = el("div", null, "row");
        row.appendChild(action(t("send"), function () {
          return api("POST", "/api/send", {to: to.value, subject: subject.value, text: text.value})
            .then(function () { return t("sent"); });
        }, output));
        compose.appendChild(row);
        compose.appendChild(output);
        var recent = section(t("recent"));
        recent.appendChild(grid(data.recent.map(function (entry) {
          return {timestamp: entry.timestamp, event: entry.event, provider: entry.provider,
                  subject: entry.subject, to: entry.to, error: entry.error && entry.error.message};
        })));
        [account, health, counts, compose, recent].forEach(function (node) { view.appendChild(node); });
      });
    },
    accounts: function (view) {
      return api("GET", "/api/accounts").then(function (data) {
        var account = section(t("account"));
        account.appendChild(keyValues(data.account));
        var output = el("pre");
        var row = el("div", null, "row");
        row.appendChild(action(t("check"), function () {
          return api("POST", "/api/accounts/check", {}).then(function (result) { return result.health; });
        }, output));
        account.appendChild(row);
        account.appendChild(output);
        var servers = section(t("servers"));
        servers.appendChild(keyValues(data.servers || {}));
        var providers = section(t("providers"));
        providers.appendChild(el("p", data.registered_providers.join(", ")));
        [account, servers, providers].forEach(function (node) { view.appendChild(node); });
      });
    },
    templates: function (view) {
      return api("GET", "/api/templates").then(function (data) {
        var directories = section(t("directories"));
        directories.appendChild(el("pre", data.directories.join("\n")));
        view.appendChild(directories);
        if (!data.templates.length) { view.appendChild(el("p", t("none"), "muted")); }
        data.templates.forEach(function (template) {
          var block = section(template.name);
          if (template.error) {
            block.appendChild(el("p", template.error, "problem"));
            view.appendChild(block);
            return;
          }
          block.appendChild(grid(template.variables));
          block.appendChild(el("p", "subject: " + show(template.subject), "muted"));
          var context = field(block, t("context"), true);
          context.value = "{}";
          var output = el("pre");
          var row = el("div", null, "row");
          row.appendChild(action(t("render"), function () {
            var request = {name: template.name, context: JSON.parse(context.value || "{}")};
            return api("POST", "/api/templates/render", request)
              .then(function (rendered) {
                return "subject: " + show(rendered.subject) + "\n\n--- text ---\n" + show(rendered.text) +
                  "\n\n--- html (source) ---\n" + show(rendered.html);
              });
          }, output));
          block.appendChild(row);
          block.appendChild(output);
          view.appendChild(block);
        });
      });
    },
    triggers: function (view) {
      return api("GET", "/api/triggers").then(function (data) {
        var events = section(t("events"));
        events.appendChild(el("p", data.events.join(", ")));
        var subscriptions = section(t("subscriptions"));
        subscriptions.appendChild(grid(data.subscriptions));
        var backends = section(t("backends"));
        backends.appendChild(grid(data.backends));
        var output = el("pre");
        var row = el("div", null, "row");
        row.appendChild(action(t("poll"), function () { return api("POST", "/api/triggers/poll", {}); }, output));
        backends.appendChild(row);
        backends.appendChild(output);
        [events, subscriptions, backends].forEach(function (node) { view.appendChild(node); });
      });
    },
    policies: function (view) {
      return api("GET", "/api/policies").then(function (data) {
        var block = section(t("policy"));
        block.appendChild(el("p", t("policyNote"), "muted"));
        var inputs = {};
        Object.keys(data).forEach(function (name) {
          inputs[name] = field(block, name);
          var value = data[name] === null ? "" : data[name];
          inputs[name].value = Array.isArray(value) ? value.join(", ") : value;
        });
        var output = el("pre");
        var row = el("div", null, "row");
        row.appendChild(action(t("save"), function () {
          var policy = {};
          Object.keys(inputs).forEach(function (name) {
            var value = inputs[name].value.trim();
            if (!value) { policy[name] = null; return; }
            policy[name] = name.indexOf("allowed_") === 0
              ? value.split(",").map(function (part) { return part.trim(); }).filter(Boolean)
              : Number(value);
          });
          return api("POST", "/api/policies", policy);
        }, output));
        block.appendChild(row);
        block.appendChild(output);
        view.appendChild(block);
      });
    },
    projects: function (view) {
      return api("GET", "/api/projects").then(function (data) {
        var block = section(t("layer"));
        if (data.layer) { block.appendChild(keyValues(data.layer)); }
        else { block.appendChild(el("p", data.problem, "muted")); }
        view.appendChild(block);
      });
    },
    logs: function (view) {
      return api("GET", "/api/logs?lines=200").then(function (data) {
        var log = section(t("log"));
        log.appendChild(el("p", data.log_file, "muted"));
        log.appendChild(el("pre", data.lines.join("\n") || t("none")));
        var audit = section(t("audit"));
        audit.appendChild(el("p", data.audit_file, "muted"));
        audit.appendChild(grid(data.audit.map(function (entry) {
          return {timestamp: entry.timestamp, event: entry.event, provider: entry.provider, sender: entry.sender,
                  to: entry.to, subject: entry.subject, error: entry.error && entry.error.message};
        }).reverse()));
        [log, audit].forEach(function (node) { view.appendChild(node); });
      });
    },
    settings: function (view) {
      return api("GET", "/api/settings").then(function (data) {
        var block = section(t("settings"));
        block.appendChild(keyValues(data));
        view.appendChild(block);
      });
    }
  };

  function render() {
    var navigation = document.getElementById("navigation");
    var view = document.getElementById("view");
    navigation.textContent = "";
    view.textContent = "";
    document.getElementById("language").textContent = language === "en" ? "中文" : "English";
    PAGES.forEach(function (name) {
      var button = el("button", t(name), name === current ? "current" : "");
      button.type = "button";
      button.addEventListener("click", function () { current = name; render(); });
      navigation.appendChild(button);
    });
    if (!token) { view.appendChild(el("p", t("noToken"), "problem")); return; }
    views[current](view).catch(function (error) { view.appendChild(el("p", error.message, "problem")); });
  }

  document.getElementById("language").addEventListener("click", function () {
    language = language === "en" ? "zh" : "en";
    localStorage.setItem("mail-thunder-language", language);
    render();
  });
  render();
}());
"""
