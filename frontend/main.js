$(document).ready(function () {
  // Initialize Eel backend connection
  if (window.eel && eel.init) {
    eel.init()();
  }

  // Textillate animations
  $(".text").textillate({
    loop: true,
    speed: 1500,
    sync: true,
    in: { effect: "bounceIn" },
    out: { effect: "bounceOut" },
  });

  $(".siri-message").textillate({
    loop: true,
    sync: true,
    in: { effect: "fadeInUp", sync: true },
    out: { effect: "fadeOutUp", sync: true },
  });

  // SiriWave visualizer
  var siriWave = new SiriWave({
    container: document.getElementById("siri-container"),
    width: 700,
    style: "ios9",
    amplitude: "1",
    speed: "0.30",
    height: 180,
    autostart: true,
    waveColor: "#00e5ff",
    waveOffset: 0,
    rippleEffect: true,
    rippleColor: "#ffffff",
  });

  // =====================================================================
  // RESPONSE UI
  // =====================================================================

  function createResponseBox() {
    var existing = document.getElementById("jarvisResponseBox");

    if (existing) {
      return existing;
    }

    var box = document.createElement("div");
    box.id = "jarvisResponseBox";

    box.style.cssText = `
      margin: 12px auto 0 auto;
      width: min(680px, 90%);
      min-height: 45px;
      padding: 12px 16px;
      border: 1px solid #00e5ff;
      border-radius: 10px;
      background: rgba(3, 12, 28, 0.92);
      color: #e8fbff;
      font-family: monospace;
      font-size: 14px;
      line-height: 1.5;
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.18);
      white-space: pre-wrap;
      word-break: break-word;
      text-align: left;
      display: none;
      position: relative;
      z-index: 20;
    `;

    var chatbox = document.getElementById("chatbox");

    if (chatbox) {
      var parent = chatbox.closest("form") ||
                   chatbox.closest(".input-group") ||
                   chatbox.parentElement;

      if (parent && parent.parentElement) {
        parent.parentElement.appendChild(box);
      } else {
        document.body.appendChild(box);
      }
    } else {
      document.body.appendChild(box);
    }

    return box;
  }

  function extractResponseText(res) {
    if (res === null || res === undefined) {
        return "";
    }

    // Direct string response
    if (typeof res === "string") {
        return res;
    }

    // Direct primitive response
    if (typeof res === "number" || typeof res === "boolean") {
        return String(res);
    }

    // Object response
    if (typeof res === "object") {

        // IMPORTANT:
        // spoken is the actual natural-language answer
        if (res.spoken !== undefined && res.spoken !== null) {
            const spoken = String(res.spoken).trim();
            if (spoken) {
                return spoken;
            }
        }

        // Standard message
        if (res.message !== undefined && res.message !== null) {
            const message = String(res.message).trim();
            if (message) {
                return message;
            }
        }

        // Alternative response field
        if (res.response !== undefined && res.response !== null) {
            const response = String(res.response).trim();
            if (response) {
                return response;
            }
        }

        // Text field
        if (res.text !== undefined && res.text !== null) {
            const text = String(res.text).trim();
            if (text) {
                return text;
            }
        }

        // Nested result
        if (res.result !== undefined && res.result !== null) {

            if (typeof res.result === "string") {
                return res.result;
            }

            if (typeof res.result === "object") {

                if (res.result.spoken) {
                    return String(res.result.spoken);
                }

                if (res.result.message) {
                    return String(res.result.message);
                }

                if (res.result.response) {
                    return String(res.result.response);
                }

                if (res.result.text) {
                    return String(res.result.text);
                }
            }
        }

        // Nested data
        if (res.data !== undefined && res.data !== null) {

            if (typeof res.data === "string") {
                return res.data;
            }

            if (typeof res.data === "object") {

                if (res.data.spoken) {
                    return String(res.data.spoken);
                }

                if (res.data.message) {
                    return String(res.data.message);
                }

                if (res.data.response) {
                    return String(res.data.response);
                }

                if (res.data.text) {
                    return String(res.data.text);
                }
            }
        }
    }

    return "";
}

  function showAssistantResponse(res) {
    console.log("SHOW ASSISTANT RESPONSE CALLED:", res);
    console.trace("SHOW ASSISTANT RESPONSE STACK");
    console.log("JARVIS RESPONSE RECEIVED:", res);

    const text = extractResponseText(res);

    if (!text || !text.trim()) {
        console.warn("JARVIS: Empty response received", res);
        return;
    }

    const finalText = text.trim();

    console.log("JARVIS RESPONSE DISPLAY:", finalText);

    const box = createResponseBox();

    if (box) {
    box.textContent = "JARVIS: " + finalText;
    box.style.display = "block";
}

    // Main/home response area
    $("#homeCurrentTask").text(finalText);

    // Existing response elements
    $("#result").text(finalText);
    $("#response").text(finalText);
    $("#jarvisResponse").text(finalText);

    // Keep latest response visible
    clearTimeout(window.jarvisResponseTimer);

    window.jarvisResponseTimer = setTimeout(function () {
        // Intentionally do not hide response.
    }, 1000);
}

  // ---------------------------------------------------------------------
  // Expose response handlers so Python/Eel can call them directly.
  // These are harmless even if backend currently does not use them.
  // ---------------------------------------------------------------------

  if (window.eel && eel.expose) {
    eel.expose(showAssistantResponse, "showAssistantResponse");
    eel.expose(showAssistantResponse, "displayResponse");
    eel.expose(showAssistantResponse, "updateAssistantResponse");
    eel.expose(showAssistantResponse, "setAssistantResponse");
  }

  // =====================================================================
  // 1. Navigation & Panel Switcher
  // =====================================================================

  var panelTitles = {
    "panel-home": "HOME DASHBOARD",
    "panel-agents": "AUTONOMOUS AGENTS HUB",
    "panel-automation": "AUTOMATION & TASK SCHEDULER",
    "panel-browser": "BROWSER & WEB RESEARCH",
    "panel-files": "FILE SYSTEM & WORKSPACE",
    "panel-terminal": "SYSTEM TERMINAL & PROCESSES",
    "panel-github": "GITHUB & GIT TELEMETRY",
    "panel-google": "GOOGLE WORKSPACE",
    "panel-aitools": "AI COGNITIVE TOOLS",
    "panel-vision": "COMPUTER VISION & PERCEPTION",
    "panel-memory": "COGNITIVE MEMORY STORE",
    "panel-settings": "SETTINGS & CONFIGURATION"
  };

  $(".sidebar-nav .nav-item").click(function () {
    var targetPanel = $(this).data("panel");
    if (!targetPanel) return;

    $(".sidebar-nav .nav-item").removeClass("active");
    $(this).addClass("active");

    $(".jarvis-panel").removeClass("active");
    $("#" + targetPanel).addClass("active");

    $("#currentPanelTitle").text(panelTitles[targetPanel] || "DASHBOARD");

    switch (targetPanel) {
      case "panel-home":
        loadHomeActivityLogs();
        break;

      case "panel-automation":
        loadAutomations();
        break;

      case "panel-files":
        loadFiles($("#currentFolderInput").val() || ".");
        break;

      case "panel-terminal":
        loadProcesses();
        break;

      case "panel-github":
        loadGitTelemetry();
        break;

      case "panel-vision":
        loadVisionTelemetry();
        break;

      case "panel-memory":
        loadMemories();
        break;

      case "panel-settings":
        loadSettingsConfig();
        break;
    }
  });

  // =====================================================================
  // 2. Command Dispatcher & Voice Controls
  // =====================================================================

  function PlayAssistant(message) {
  if (!message || message.trim() === "") return;

  $("#Oval").attr("hidden", true);
  $("#SiriWave").attr("hidden", false);

  $("#chatbox").val("");
  $("#MicBtn").attr("hidden", false);
  $("#SendBtn").attr("hidden", true);

  // ---------------------------------------------------------
  // Create a guaranteed JARVIS response box if it doesn't exist
  // ---------------------------------------------------------
  var responseBox = $("#jarvisCommandResponse");

  if (responseBox.length === 0) {
    responseBox = $(
      '<div id="jarvisCommandResponse" style="' +
        'margin: 12px auto 20px auto;' +
        'max-width: 840px;' +
        'padding: 14px 20px;' +
        'border: 1px solid #00e5ff;' +
        'border-radius: 14px;' +
        'background: rgba(5, 15, 30, 0.85);' +
        'color: #e8faff;' +
        'font-family: monospace;' +
        'font-size: 15px;' +
        'box-shadow: 0 0 18px rgba(0,229,255,0.25);' +
        'display: none;' +
        '"></div>'
    );

    // Put response directly below command input
    $("#chatbox").closest("div").after(responseBox);
  }

  // Show processing state
  responseBox
    .stop(true, true)
    .show()
    .text("JARVIS: Processing command...");

  console.log("JARVIS COMMAND SENT:", message);

  if (window.eel && eel.takeAllCommands) {

    eel.takeAllCommands(message);

  } else {

    responseBox
      .show()
      .text("JARVIS: Backend connection unavailable.");

    $("#SiriWave").attr("hidden", true);
    $("#Oval").attr("hidden", false);
  }
}

  function ShowHideButton(message) {
    if (!message || message.length === 0) {
      $("#MicBtn").attr("hidden", false);
      $("#SendBtn").attr("hidden", true);
    } else {
      $("#MicBtn").attr("hidden", true);
      $("#SendBtn").attr("hidden", false);
    }
  }

  $("#chatbox").keyup(function () {
    ShowHideButton($(this).val());
  });

  $("#SendBtn").click(function () {
    PlayAssistant($("#chatbox").val());
  });

  $("#chatbox").on("keydown", function (e) {
    if (e.key === "Enter" || e.keyCode === 13) {
      e.preventDefault();
      PlayAssistant($(this).val());
    }
  });

  $("#MicBtn").click(function () {

    if (window.eel && eel.play_assistant_sound) {
      eel.play_assistant_sound();
    }

    $("#Oval").attr("hidden", true);
    $("#SiriWave").attr("hidden", false);

    if (window.eel && eel.takeAllCommands) {

      eel.takeAllCommands()(function (res) {

        console.log("JARVIS voice response:", res);

        if (res !== undefined && res !== null) {
          showAssistantResponse(res);
        }

        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
      });
    }
  });

  // Hotkey summon: Win+J / Meta+J
  document.addEventListener("keyup", function (e) {
    if (e.key === "j" && e.metaKey) {

      if (window.eel && eel.play_assistant_sound) {
        eel.play_assistant_sound();
      }

      $("#Oval").attr("hidden", true);
      $("#SiriWave").attr("hidden", false);

      if (window.eel && eel.takeAllCommands) {

        eel.takeAllCommands()(function (res) {

          console.log("JARVIS hotkey response:", res);

          if (res !== undefined && res !== null) {
            showAssistantResponse(res);
          }

          $("#Oval").attr("hidden", false);
          $("#SiriWave").attr("hidden", true);
        });
      }
    }
  }, false);

  // Quick Action Buttons on Home
  $(".quick-act-btn").click(function () {
    var cmd = $(this).data("cmd");
    var action = $(this).data("action");

    if (cmd) {
      PlayAssistant(cmd);

    } else if (action && window.eel && eel[action]) {

      eel[action]()(function (res) {

        console.log("Quick action response:", res);

        if (res && res.message) {
          showAssistantResponse(res);
        }
      });
    }
  });

  // =====================================================================
  // 3. Real-time Telemetry Poller
  // =====================================================================

  function fetchLiveTelemetry() {
    if (window.eel && eel.getSystemMetrics) {

      eel.getSystemMetrics()(function (data) {

        if (data && data.success && data.system) {

          var sys = data.system;

          if (sys.ram) {

            var ramPct = sys.ram.percent_used;

            $("#topRamPill").html(
              '<i class="bi bi-memory"></i> RAM: ' +
              ramPct +
              '%'
            );

            $("#cardRamVal").text(ramPct + "%");

            $("#cardRamSub").text(
              sys.ram.used_gb +
              " GB / " +
              sys.ram.total_gb +
              " GB Used"
            );

            $("#sidebarRamBar").css(
              "width",
              ramPct + "%"
            );

            $("#sidebarRamText").text(
              "RAM: " +
              ramPct +
              "%"
            );
          }

          var arch = sys.machine || "AMD64";

          $("#topCpuPill").html(
            '<i class="bi bi-cpu"></i> CPU: Active'
          );

          $("#cardCpuVal").text("ACTIVE");

          $("#cardCpuSub").text(
            arch +
            " / " +
            (
              sys.processor
                ? sys.processor.substring(0, 18) + "..."
                : ""
            )
          );

          if (sys.disk) {

            $("#topDiskPill").html(
              '<i class="bi bi-hdd"></i> DISK: ' +
              sys.disk.percent_used +
              "%"
            );

            $("#cardDiskVal").text(
              sys.disk.percent_used + "%"
            );

            $("#cardDiskSub").text(
              sys.disk.free_gb +
              " GB Free on " +
              sys.disk.drive
            );
          }

          if (
            data.battery &&
            data.battery.percent !== undefined
          ) {

            var bat = data.battery;

            $("#cardBatVal").text(
              bat.percent + "%"
            );

            $("#cardBatSub").text(
              bat.is_charging
                ? "AC Connected (Charging)"
                : "On Battery Power"
            );

            $("#sidebarBatteryText").text(
              "BAT: " +
              bat.percent +
              "%"
            );
          }

          if (data.network) {

            var isOnline = data.network.online;

            $("#topNetPill").html(
              '<i class="bi bi-wifi"></i> NET: ' +
              (
                isOnline
                  ? "ONLINE"
                  : "OFFLINE"
              )
            );
          }

          if (data.active_window) {
            $("#homeActiveWin").text(
              data.active_window
            );
          }
        }
      });
    }
  }

  setInterval(fetchLiveTelemetry, 3500);
  setTimeout(fetchLiveTelemetry, 800);

  // =====================================================================
  // 4. Panel 1: Home Activity Log Stream
  // =====================================================================

  function loadHomeActivityLogs() {

    if (window.eel && eel.getActivityLogs) {

      eel.getActivityLogs(10)(function (res) {

        if (
          res &&
          res.success &&
          res.logs &&
          res.logs.length > 0
        ) {

          var rows = "";

          res.logs.forEach(function (log) {

            var isSuccess =
              log.status === "SUCCESS";

            var badgeClass =
              isSuccess
                ? "status-success"
                : "status-failed";

            var timeStr =
              log.timestamp
                ? log.timestamp.split("T")[1] ||
                  log.timestamp
                : "";

            if (
              timeStr &&
              timeStr.length > 8
            ) {
              timeStr =
                timeStr.substring(0, 8);
            }

            rows += `<tr>
              <td class="font-monospace text-muted small">
                ${timeStr || log.timestamp}
              </td>

              <td class="text-light fw-bold">
                ${log.command}
              </td>

              <td>
                <span class="badge bg-dark border border-secondary text-cyan">
                  ${log.tool || log.intent}
                </span>
              </td>

              <td>
                <span class="status-tag ${badgeClass}">
                  ${log.status}
                </span>
              </td>

              <td
                class="text-truncate"
                style="max-width: 250px;"
                title="${log.result}"
              >
                ${log.result}
              </td>
            </tr>`;
          });

          $("#homeActivityTbody").html(rows);

        } else {

          $("#homeActivityTbody").html(
            '<tr>' +
            '<td colspan="5" class="text-center text-muted py-3">' +
            'No activity logs recorded yet.' +
            '</td>' +
            '</tr>'
          );
        }
      });
    }
  }

  $("#homeRefreshLogsBtn").click(
    loadHomeActivityLogs
  );

  setTimeout(
    loadHomeActivityLogs,
    1200
  );

  // =====================================================================
  // 5. Panel 2: Agents Hub
  // =====================================================================

  $(".agent-btn").click(function () {

    var tool = $(this).data("tool");
    var cmd = $(this).data("cmd");
    var action = $(this).data("action");
    var paramAttr = $(this).data("param");

    var params =
      paramAttr
        ? (
            typeof paramAttr === "object"
              ? paramAttr
              : JSON.parse(paramAttr)
          )
        : {};

    var targetBox =
      $(this)
        .closest(".agent-body")
        .find(".agent-output-box");

    if (cmd) {
      PlayAssistant(cmd);
      return;
    }

    if (
      action &&
      window.eel &&
      eel[action]
    ) {

      targetBox.text(
        "Executing " +
        action +
        "..."
      );

      eel[action]()(function (res) {

        targetBox.text(
          res
            ? JSON.stringify(
                res,
                null,
                2
              )
            : "Executed."
        );
      });

      return;
    }

    if (
      tool &&
      window.eel &&
      eel.runAgentAction
    ) {

      targetBox.text(
        "Executing " +
        tool +
        "..."
      );

      eel.runAgentAction(
        "agent",
        tool,
        params
      )(function (res) {

        if (res) {

          var out =
            res.message ||
            JSON.stringify(
              res.data,
              null,
              2
            );

          targetBox.text(out);
        }
      });
    }
  });

  // =====================================================================
  // 6. Panel 3: Automation Scheduler
  // =====================================================================

  function loadAutomations() {

    if (
      window.eel &&
      eel.getAutomationsList
    ) {

      eel.getAutomationsList()(function (res) {

        if (
          res &&
          res.success &&
          res.automations
        ) {

          var rows = "";

          if (
            res.automations.length === 0
          ) {

            rows =
              '<tr>' +
              '<td colspan="5" class="text-center text-muted py-3">' +
              'No custom automations registered. Use the form to create one.' +
              '</td>' +
              '</tr>';

          } else {

            res.automations.forEach(
              function (a) {

                var isActive =
                  a.status === "ACTIVE";

                rows += `<tr>

                  <td class="fw-bold text-light">
                    ${a.name}
                  </td>

                  <td>
                    <span class="badge bg-secondary">
                      ${a.trigger_type}
                      (${a.interval_sec}s)
                    </span>
                  </td>

                  <td class="font-monospace small text-cyan">
                    ${a.command}
                  </td>

                  <td>
                    <span class="status-tag ${
                      isActive
                        ? "status-success"
                        : "status-failed"
                    }">
                      ${a.status}
                    </span>
                  </td>

                  <td>
                    <button
                      class="btn btn-sm btn-outline-cyan toggle-auto-btn"
                      data-id="${a.id}"
                    >
                      Toggle
                    </button>
                  </td>

                </tr>`;
              }
            );
          }

          $("#automationsTbody").html(rows);

          $(".toggle-auto-btn").click(
            function () {

              var autoId =
                $(this).data("id");

              if (
                window.eel &&
                eel.toggleAutomationTask
              ) {

                eel.toggleAutomationTask(
                  autoId
                )(function () {

                  loadAutomations();

                });
              }
            }
          );
        }
      });
    }
  }

  $("#refreshAutomationsBtn").click(
    loadAutomations
  );

  $("#saveAutomationBtn").click(
    function () {

      var name =
        $("#autoNameInput")
          .val()
          .trim();

      var type =
        $("#autoTypeSelect")
          .val();

      var interval =
        parseInt(
          $("#autoIntervalInput").val()
        ) || 0;

      var cmd =
        $("#autoCmdInput")
          .val()
          .trim();

      if (
        name &&
        cmd &&
        window.eel &&
        eel.createAutomationTask
      ) {

        eel.createAutomationTask(
          name,
          type,
          cmd,
          interval
        )(function (res) {

          alert(res.message);

          $("#autoNameInput").val("");
          $("#autoCmdInput").val("");

          loadAutomations();
        });
      }
    }
  );

  // =====================================================================
  // 7. Panel 4: Browser & Web Tools
  // =====================================================================

  $("#browserSearchBtn").click(
    function () {

      var q =
        $("#browserSearchInput")
          .val()
          .trim();

      var eng =
        $("#searchEngineSelect")
          .val();

      if (
        q &&
        window.eel &&
        eel.searchWebBrowser
      ) {

        eel.searchWebBrowser(
          q,
          eng
        )();
      }
    }
  );

  $("#directUrlBtn").click(
    function () {

      var url =
        $("#directUrlInput")
          .val()
          .trim();

      if (
        url &&
        window.eel &&
        eel.searchWebBrowser
      ) {

        eel.searchWebBrowser(
          url,
          "google"
        )();
      }
    }
  );

  $("#scrapeUrlBtn").click(
    function () {

      var url =
        $("#scrapeUrlInput")
          .val()
          .trim();

      if (!url) return;

      $("#scrapeResultBox").text(
        "Scraping webpage and generating AI summary..."
      );

      if (
        window.eel &&
        eel.scrapeWebPage
      ) {

        eel.scrapeWebPage(
          url
        )(function (res) {

          if (
            res &&
            res.success &&
            res.data
          ) {

            var d = res.data;

            var text =
              `TITLE: ${d.title}
URL: ${d.url}
PARAGRAPHS: ${d.paragraph_count} (${d.char_count} chars)

EXECUTIVE SUMMARY:
${d.summary}

SNIPPET:
${d.snippet}`;

            $("#scrapeResultBox")
              .text(text);

          } else {

            $("#scrapeResultBox").text(
              "Scraping error: " +
              (
                res.error ||
                res.message
              )
            );
          }
        });
      }
    }
  );

  // =====================================================================
  // 8. Panel 5: File System & Workspace
  // =====================================================================

  function loadFiles(folder) {

    if (
      window.eel &&
      eel.getFileList
    ) {

      $("#filesTableBody").html(
        '<tr>' +
        '<td colspan="4" class="text-center text-muted py-3">' +
        'Reading directory...' +
        '</td>' +
        '</tr>'
      );

      eel.getFileList(
        folder
      )(function (res) {

        if (
          res &&
          res.success &&
          res.data &&
          res.data.items
        ) {

          var items =
            res.data.items;

          $("#fileCountBadge").text(
            items.length +
            " items"
          );

          var rows = "";

          items.forEach(
            function (it) {

              var icon =
                it.type === "directory"
                  ? "bi-folder-fill text-warning"
                  : "bi-file-earmark-code text-cyan";

              var sizeStr =
                it.type === "directory"
                  ? "--"
                  : (
                      it.size < 1024
                        ? it.size + " B"
                        : (
                            it.size / 1024
                          ).toFixed(1) +
                          " KB"
                    );

              rows += `<tr>

                <td class="font-monospace small text-light">
                  <i class="bi ${icon} me-1"></i>
                  ${it.name}
                </td>

                <td>
                  <span class="badge bg-dark border border-secondary">
                    ${it.type}
                  </span>
                </td>

                <td class="font-monospace small text-muted">
                  ${sizeStr}
                </td>

                <td>

                  ${
                    it.type === "file"
                      ? `
                        <button
                          class="btn btn-sm btn-outline-cyan py-0 read-file-btn"
                          data-path="${it.path}"
                        >
                          <i class="bi bi-eye"></i>
                        </button>
                      `
                      : `
                        <button
                          class="btn btn-sm btn-outline-secondary py-0 open-dir-btn"
                          data-path="${it.path}"
                        >
                          <i class="bi bi-folder2-open"></i>
                        </button>
                      `
                  }

                </td>

              </tr>`;
            }
          );

          $("#filesTableBody")
            .html(rows);

          $(".read-file-btn").click(
            function () {

              var p =
                $(this).data("path");

              $("#previewFileName")
                .text(p);

              $("#filePreviewBox")
                .text(
                  "Reading " +
                  p +
                  "..."
                );

              if (
                window.eel &&
                eel.readFileContent
              ) {

                eel.readFileContent(
                  p
                )(function (r) {

                  if (
                    r &&
                    r.success &&
                    r.data
                  ) {

                    $("#filePreviewBox")
                      .text(
                        r.data.content
                      );

                  } else {

                    $("#filePreviewBox")
                      .text(
                        "Error: " +
                        (
                          r.error ||
                          r.message
                        )
                      );
                  }
                });
              }
            }
          );

          $(".open-dir-btn").click(
            function () {

              var dir =
                $(this).data("path");

              $("#currentFolderInput")
                .val(dir);

              loadFiles(dir);
            }
          );
        }
      });
    }
  }

  $("#browseFolderBtn").click(
    function () {
      loadFiles(
        $("#currentFolderInput").val()
      );
    }
  );

  $("#refreshFilesBtn").click(
    function () {
      loadFiles(
        $("#currentFolderInput").val()
      );
    }
  );

  $("#searchFilesBtn").click(
    function () {

      var kw =
        $("#fileSearchKeyword")
          .val()
          .trim();

      var folder =
        $("#currentFolderInput")
          .val();

      if (
        kw &&
        window.eel &&
        eel.searchFiles
      ) {

        $("#filesTableBody").html(
          '<tr>' +
          '<td colspan="4" class="text-center text-muted py-3">' +
          'Searching...' +
          '</td>' +
          '</tr>'
        );

        eel.searchFiles(
          folder,
          kw
        )(function (res) {

          if (
            res &&
            res.success &&
            res.data &&
            res.data.matches
          ) {

            var matches =
              res.data.matches;

            $("#fileCountBadge")
              .text(
                matches.length +
                " matches"
              );

            var rows = "";

            matches.forEach(
              function (m) {

                rows += `<tr>

                  <td class="font-monospace small text-light">
                    <i class="bi bi-file-earmark-code text-cyan me-1"></i>
                    ${m.name}
                  </td>

                  <td>
                    <span class="badge bg-dark border border-secondary">
                      ${m.extension}
                    </span>
                  </td>

                  <td class="font-monospace small text-muted">
                    ${(m.size / 1024).toFixed(1)} KB
                  </td>

                  <td>
                    <button
                      class="btn btn-sm btn-outline-cyan py-0 read-file-btn"
                      data-path="${m.path}"
                    >
                      <i class="bi bi-eye"></i>
                    </button>
                  </td>

                </tr>`;
              }
            );

            $("#filesTableBody")
              .html(rows);

            $(".read-file-btn").click(
              function () {

                var p =
                  $(this).data("path");

                $("#previewFileName")
                  .text(p);

                $("#filePreviewBox")
                  .text(
                    "Reading " +
                    p +
                    "..."
                  );

                eel.readFileContent(
                  p
                )(function (r) {

                  if (
                    r &&
                    r.success &&
                    r.data
                  ) {

                    $("#filePreviewBox")
                      .text(
                        r.data.content
                      );
                  }
                });
              }
            );
          }
        });
      }
    }
  );

  $("#newFileBtn").click(
    function () {

      $("#newFileType")
        .val("file");

      $("#newFileModalTitle")
        .text("Create New File");

      $("#newFilePathLabel")
        .text(
          "File Name / Relative Path"
        );

      $("#newFileContentGroup")
        .show();

      var modal =
        bootstrap.Modal
          .getOrCreateInstance(
            document.getElementById(
              "newFileModal"
            )
          );

      modal.show();
    }
  );

  $("#newFolderBtn").click(
    function () {

      $("#newFileType")
        .val("folder");

      $("#newFileModalTitle")
        .text("Create New Folder");

      $("#newFilePathLabel")
        .text(
          "Folder Name / Relative Path"
        );

      $("#newFileContentGroup")
        .hide();

      var modal =
        bootstrap.Modal
          .getOrCreateInstance(
            document.getElementById(
              "newFileModal"
            )
          );

      modal.show();
    }
  );

  $("#confirmCreateFileBtn").click(
    function () {

      var type =
        $("#newFileType").val();

      var p =
        $("#newFilePathInput")
          .val()
          .trim();

      var content =
        $("#newFileContentInput")
          .val();

      if (
        p &&
        window.eel &&
        eel.createFileOrFolder
      ) {

        eel.createFileOrFolder(
          type,
          p,
          content
        )(function (res) {

          alert(res.message);

          var modal =
            bootstrap.Modal.getInstance(
              document.getElementById(
                "newFileModal"
              )
            );

          if (modal) {
            modal.hide();
          }

          loadFiles(
            $("#currentFolderInput")
              .val()
          );
        });
      }
    }
  );

  // =====================================================================
  // 9. Panel 6: Terminal & Dangerous Command Safeguard
  // =====================================================================

  var pendingDangerousCmd = null;

  function appendTerminalOutput(
    line,
    isError
  ) {

    var screen =
      document.getElementById(
        "terminalScreenOutput"
      );

    if (screen) {

      var colorClass =
        isError
          ? "text-danger"
          : "text-light";

      screen.innerHTML +=
        `\n<span class="${colorClass}">${line}</span>`;

      screen.scrollTop =
        screen.scrollHeight;
    }
  }

  function executeTerminal(
    cmd,
    allowDangerous
  ) {

    if (!cmd) return;

    appendTerminalOutput(
      `PS > ${cmd}`,
      false
    );

    if (
      window.eel &&
      eel.runTerminalCommand
    ) {

      eel.runTerminalCommand(
        cmd,
        allowDangerous
      )(function (res) {

        if (
          res.error ===
          "ConfirmationRequired"
        ) {

          pendingDangerousCmd = cmd;

          $("#dangerModalCmd")
            .text(cmd);

          var modal =
            bootstrap.Modal
              .getOrCreateInstance(
                document.getElementById(
                  "dangerConfirmModal"
                )
              );

          modal.show();

        } else {

          var out =
            res.data &&
            res.data.stdout
              ? res.data.stdout
              : res.message;

          appendTerminalOutput(
            out,
            !res.success
          );
        }
      });
    }
  }

  $("#executeTerminalBtn").click(
    function () {

      var cmd =
        $("#terminalInputBox")
          .val()
          .trim();

      if (cmd) {

        executeTerminal(
          cmd,
          false
        );

        $("#terminalInputBox")
          .val("");
      }
    }
  );

  $("#terminalInputBox").keypress(
    function (e) {

      if (e.which === 13) {

        var cmd =
          $(this)
            .val()
            .trim();

        if (cmd) {

          executeTerminal(
            cmd,
            false
          );

          $(this).val("");
        }
      }
    }
  );

  $("#confirmDangerBtn").click(
    function () {

      if (pendingDangerousCmd) {

        executeTerminal(
          pendingDangerousCmd,
          true
        );

        pendingDangerousCmd = null;
      }

      var modal =
        bootstrap.Modal.getInstance(
          document.getElementById(
            "dangerConfirmModal"
          )
        );

      if (modal) {
        modal.hide();
      }
    }
  );

  $("#clearTerminalBtn").click(
    function () {

      var screen =
        document.getElementById(
          "terminalScreenOutput"
        );

      if (screen) {

        screen.innerHTML =
          "JARVIS AI OS Terminal [Version 2.0.0]\n" +
          "Screen cleared.\n";
      }
    }
  );

  function loadProcesses() {

    if (
      window.eel &&
      eel.getProcessList
    ) {

      $("#processTbody").html(
        '<tr>' +
        '<td colspan="3" class="text-center text-muted py-3">' +
        'Querying tasklist...' +
        '</td>' +
        '</tr>'
      );

      eel.getProcessList()(
        function (res) {

          if (
            res &&
            res.success &&
            res.data &&
            res.data.processes
          ) {

            var procs =
              res.data.processes;

            $("#processCountBadge")
              .text(
                procs.length +
                " active"
              );

            var rows = "";

            procs
              .slice(0, 30)
              .forEach(
                function (p) {

                  rows += `<tr>

                    <td class="font-monospace small text-cyan">
                      ${p.name}
                    </td>

                    <td class="font-monospace small text-muted">
                      ${p.pid}
                    </td>

                    <td class="font-monospace small text-light">
                      ${p.mem}
                    </td>

                  </tr>`;
                }
              );

            $("#processTbody")
              .html(rows);
          }
        }
      );
    }
  }

  $("#refreshProcessesBtn")
    .click(loadProcesses);

  // =====================================================================
  // 10. Panel 7: GitHub Workspace
  // =====================================================================

  function loadGitTelemetry() {

    if (
      window.eel &&
      eel.getGitTelemetry
    ) {

      eel.getGitTelemetry()(
        function (res) {

          if (
            res &&
            res.success
          ) {

            if (res.repo) {

              $("#gitRepoName")
                .text(
                  res.repo.name ||
                  "Jarvis"
                );

              $("#gitRepoPath")
                .text(
                  res.repo.path ||
                  "."
                );

              $("#gitBranchName")
                .text(
                  res.repo.branch ||
                  "main"
                );
            }

            if (res.status) {

              var lines =
                res.status.status_lines ||
                [];

              $("#gitChangesCount")
                .text(
                  lines.length +
                  " Files"
                );

              $("#gitChangesSummary")
                .text(
                  lines.length === 0
                    ? "Working tree clean"
                    : lines.length +
                      " uncommitted changes"
                );
            }

            if (res.diff) {

              $("#gitDiffBox")
                .text(
                  res.diff.diff ||
                  "Working tree clean. No unstaged diff."
                );
            }

            if (res.logs) {

              var logHtml = "";

              res.logs.forEach(
                function (c) {

                  logHtml +=
                    `<div class="p-1 mb-1 border-bottom border-secondary font-monospace small text-light">
                      <i class="bi bi-git text-cyan"></i>
                      ${c}
                    </div>`;
                }
              );

              $("#gitLogList").html(
                logHtml ||
                '<div class="text-muted small">No commits found.</div>'
              );
            }
          }
        }
      );
    }
  }

  $("#refreshGitBtn")
    .click(loadGitTelemetry);

  $("#createCommitBtn").click(
    function () {

      var msg =
        $("#commitMsgInput")
          .val()
          .trim();

      var confirmed =
        $("#confirmCommitCheckbox")
          .is(":checked");

      if (!msg) {

        alert(
          "Please provide a commit message."
        );

        return;
      }

      if (!confirmed) {

        alert(
          "Please check the confirmation box to approve staging and committing."
        );

        return;
      }

      if (
        window.eel &&
        eel.executeGitCommit
      ) {

        eel.executeGitCommit(
          msg,
          true
        )(function (res) {

          alert(res.message);

          $("#commitMsgInput")
            .val("");

          $("#confirmCommitCheckbox")
            .prop(
              "checked",
              false
            );

          loadGitTelemetry();
        });
      }
    }
  );

  $("#runTestsBtn").click(
    function () {

      $("#testResultBox")
        .text(
          "Running automated test suite (test_router.py)..."
        );

      if (
        window.eel &&
        eel.runTestSuite
      ) {

        eel.runTestSuite(
          "test_router.py"
        )(function (res) {

          if (res) {

            var out =
              (
                res.success
                  ? "[PASS] "
                  : "[FAIL] "
              ) +
              res.message +
              "\n" +
              (
                res.data
                  ? res.data.stdout
                  : ""
              );

            $("#testResultBox")
              .text(out);
          }
        });
      }
    }
  );

  // =====================================================================
  // 11. Panel 9: AI Cognitive Tools
  // =====================================================================

  var selectedAiTool =
    "summarize";

  $(".ai-tool-tab").click(
    function () {

      $(".ai-tool-tab")
        .removeClass("active");

      $(this)
        .addClass("active");

      selectedAiTool =
        $(this).data("tool");
    }
  );

  $("#runAiToolBtn").click(
    function () {

      var prompt =
        $("#aiToolInputBox")
          .val()
          .trim();

      if (!prompt) return;

      $("#aiToolOutputBox")
        .text(
          "Transmitting request to AI core..."
        );

      if (
        window.eel &&
        eel.runAiToolAction
      ) {

        eel.runAiToolAction(
          selectedAiTool,
          prompt
        )(function (res) {

          if (
            res &&
            res.success
          ) {

            $("#aiToolOutputBox")
              .text(
                res.response
              );

          } else {

            $("#aiToolOutputBox")
              .text(
                "Error: " +
                (
                  res.error ||
                  res.message
                )
              );
          }
        });
      }
    }
  );

  $("#copyAiOutputBtn").click(
    function () {

      var text =
        $("#aiToolOutputBox")
          .text();

      navigator.clipboard
        .writeText(text)
        .then(
          function () {
            alert(
              "Copied AI output to clipboard."
            );
          }
        );
    }
  );

  // =====================================================================
  // 12. Panel 10: Computer Vision & Perception
  // =====================================================================

  function loadVisionTelemetry() {

    if (
      window.eel &&
      eel.getVisionTelemetry
    ) {

      eel.getVisionTelemetry()(
        function (res) {

          if (
            res &&
            res.success
          ) {

            if (res.screen) {

              $("#visionResVal")
                .text(
                  res.screen.resolution ||
                  "1920x1080"
                );

              $("#visionMonitorsVal")
                .text(
                  (
                    res.screen.monitors ||
                    1
                  ) +
                  " Monitor(s) Detected"
                );

              $("#visionWindowVal")
                .text(
                  res.screen.active_window ||
                  "Desktop"
                );
            }

            var thumbs = "";

            if (
              res.screenshots &&
              res.screenshots.length > 0
            ) {

              res.screenshots.forEach(
                function (s) {

                  thumbs +=
                    `<span class="badge bg-dark border border-secondary text-cyan p-2">
                      <i class="bi bi-image"></i>
                      ${s}
                    </span>`;
                }
              );
            }

            if (
              res.webcam_frames &&
              res.webcam_frames.length > 0
            ) {

              res.webcam_frames.forEach(
                function (w) {

                  thumbs +=
                    `<span class="badge bg-dark border border-secondary text-info p-2">
                      <i class="bi bi-webcam"></i>
                      ${w}
                    </span>`;
                }
              );
            }

            $("#visionThumbnailsList")
              .html(
                thumbs ||
                "No recent captures."
              );
          }
        }
      );
    }
  }

  $("#refreshVisionBtn")
    .click(loadVisionTelemetry);

  $("#visionCaptureScreenBtn").click(
    function () {

      $("#visionAnalysisOutputBox")
        .text(
          "Capturing desktop screen..."
        );

      if (
        window.eel &&
        eel.captureScreenNow
      ) {

        eel.captureScreenNow()(
          function (res) {

            $("#visionAnalysisOutputBox")
              .text(
                JSON.stringify(
                  res,
                  null,
                  2
                )
              );

            loadVisionTelemetry();
          }
        );
      }
    }
  );

  $("#visionCaptureWebcamBtn").click(
    function () {

      $("#visionAnalysisOutputBox")
        .text(
          "Triggering OpenCV camera frame read..."
        );

      if (
        window.eel &&
        eel.captureWebcamNow
      ) {

        eel.captureWebcamNow()(
          function (res) {

            $("#visionAnalysisOutputBox")
              .text(
                JSON.stringify(
                  res,
                  null,
                  2
                )
              );

            loadVisionTelemetry();
          }
        );
      }
    }
  );

  $("#visionAnalyzeBtn").click(
    function () {

      var p =
        $("#visionImagePathInput")
          .val()
          .trim();

      var prompt =
        $("#visionImagePromptInput")
          .val()
          .trim() ||
        "Describe what you see in this image in detail.";

      if (!p) {

        alert(
          "Please provide the path to an image file."
        );

        return;
      }

      $("#visionAnalysisOutputBox")
        .text(
          "Analyzing image with computer vision..."
        );

      if (
        window.eel &&
        eel.analyzeImageNow
      ) {

        eel.analyzeImageNow(
          p,
          prompt
        )(function (res) {

          $("#visionAnalysisOutputBox")
            .text(
              res.message ||
              JSON.stringify(
                res,
                null,
                2
              )
            );
        });
      }
    }
  );

  // =====================================================================
  // 13. Panel 11: Cognitive Memory
  // =====================================================================

  function loadMemories() {

    if (
      window.eel &&
      eel.getMemoryItems
    ) {

      $("#memoryCardsList")
        .html(
          '<div class="text-muted small">' +
          'Accessing memory core...' +
          '</div>'
        );

      eel.getMemoryItems()(
        function (res) {

          if (
            res &&
            res.success &&
            res.memories &&
            res.memories.length > 0
          ) {

            var html = "";

            res.memories.forEach(
              function (mem) {

                html +=
                  `<div
                    class="memory-card-item p-2 border border-secondary rounded d-flex justify-content-between align-items-center"
                    style="background: rgba(8, 16, 32, 0.8);"
                    data-key="${mem.key.toLowerCase()}"
                    data-val="${mem.value.toLowerCase()}"
                  >

                    <div>

                      <span class="text-cyan fw-bold font-monospace">
                        ${mem.key}
                      </span>

                      <div class="text-light small mt-1">
                        ${mem.value}
                      </div>

                    </div>

                    <div class="d-flex align-items-center gap-2">

                      <span class="badge bg-secondary">
                        ${mem.category || "general"}
                      </span>

                      <button
                        class="btn btn-sm btn-outline-danger delete-mem-btn"
                        data-key="${mem.key}"
                      >
                        <i class="bi bi-trash"></i>
                      </button>

                    </div>

                  </div>`;
              }
            );

            $("#memoryCardsList")
              .html(html);

            $(".delete-mem-btn").click(
              function () {

                var k =
                  $(this).data("key");

                if (
                  window.eel &&
                  eel.deleteMemoryItem
                ) {

                  eel.deleteMemoryItem(
                    k
                  )(function () {

                    loadMemories();

                  });
                }
              }
            );

          } else {

            $("#memoryCardsList")
              .html(
                '<div class="text-muted small">' +
                'No memories stored. Teach JARVIS facts using the input box or say "remember that...".' +
                '</div>'
              );
          }
        }
      );
    }
  }

  $("#refreshMemoryBtn")
    .click(loadMemories);

  $("#memorySearchInput").keyup(
    function () {

      var q =
        $(this)
          .val()
          .toLowerCase()
          .trim();

      $(".memory-card-item").each(
        function () {

          var k =
            $(this).data("key") ||
            "";

          var v =
            $(this).data("val") ||
            "";

          if (
            k.includes(q) ||
            v.includes(q)
          ) {

            $(this).show();

          } else {

            $(this).hide();
          }
        }
      );
    }
  );

  $("#saveMemoryBtn").click(
    function () {

      var k =
        $("#memoryKeyInput")
          .val()
          .trim();

      var v =
        $("#memoryValInput")
          .val()
          .trim();

      var cat =
        $("#memoryCategorySelect")
          .val();

      if (
        k &&
        v &&
        window.eel &&
        eel.saveMemoryItem
      ) {

        eel.saveMemoryItem(
          k,
          v,
          cat
        )(function (res) {

          alert(res.message);

          $("#memoryKeyInput")
            .val("");

          $("#memoryValInput")
            .val("");

          loadMemories();
        });
      }
    }
  );

  // =====================================================================
  // 14. Panel 12: Settings & Configuration
  // =====================================================================

  function loadSettingsConfig() {

    if (
      window.eel &&
      eel.getAiConfig
    ) {

      eel.getAiConfig()(
        function (res) {

          if (
            res &&
            res.success
          ) {

            $("#settingsProviderText")
              .text(
                res.provider.toUpperCase() +
                (
                  res.is_online
                    ? " (Online)"
                    : " (Offline Fallback)"
                )
              );

            $("#settingsModelText")
              .text(res.model);

            $("#settingsVoiceSlider")
              .val(
                res.voice_rate ||
                174
              );

            $("#settingsVoiceRateVal")
              .text(
                (
                  res.voice_rate ||
                  174
                ) +
                " WPM"
              );
          }
        }
      );
    }

    if (
      window.eel &&
      eel.getSystemMetrics
    ) {

      eel.getSystemMetrics()(
        function (m) {

          if (
            m &&
            m.system
          ) {

            var sys =
              m.system;

            var text =
              `OS: ${sys.os || "Windows"} ${sys.os_version || ""}
Architecture: ${sys.machine || "AMD64"}
Python Runtime: ${sys.python || "3.12"}
Hostname: ${sys.hostname || "DESKTOP"}
Database Path: jarvis.db (SQLite3)
Wake Word Standby: Continuous`;

            $("#settingsSysInfoBox")
              .text(text);
          }
        }
      );
    }
  }

  $("#settingsVoiceSlider").on(
    "input",
    function () {

      var rate =
        $(this).val();

      $("#settingsVoiceRateVal")
        .text(
          rate +
          " WPM"
        );
    }
  );

  $("#settingsTestVoiceBtn").click(
    function () {

      var rate =
        parseInt(
          $("#settingsVoiceSlider")
            .val()
        ) || 174;

      if (
        window.eel &&
        eel.setVoiceSettings
      ) {

        eel.setVoiceSettings(
          rate,
          0
        )();
      }
    }
  );

  // =====================================================================
  // 15. Offcanvas Neural Stream Chat
  // =====================================================================

  function toggleChatDrawer() {

    var el =
      document.getElementById(
        "offcanvasChat"
      );

    if (
      el &&
      window.bootstrap
    ) {

      var bs =
        bootstrap.Offcanvas
          .getOrCreateInstance(el);

      bs.toggle();
    }
  }

  $("#topChatDrawerBtn, #ChatBtn")
    .click(toggleChatDrawer);

  $("#drawerSendBtn").click(
    function () {

      var msg =
        $("#drawerChatInput")
          .val()
          .trim();

      if (msg) {

        PlayAssistant(msg);

        $("#drawerChatInput")
          .val("");
      }
    }
  );

  $("#drawerChatInput").keypress(
    function (e) {

      if (e.which === 13) {

        var msg =
          $(this)
            .val()
            .trim();

        if (msg) {

          PlayAssistant(msg);

          $(this).val("");
        }
      }
    }
  );

  $("#SettingBtn").click(
    function () {

      $(".sidebar-nav .nav-item")
        .removeClass("active");

      $(
        '.sidebar-nav .nav-item[data-panel="panel-settings"]'
      ).addClass("active");

      $(".jarvis-panel")
        .removeClass("active");

      $("#panel-settings")
        .addClass("active");

      $("#currentPanelTitle")
        .text(
          "SETTINGS & CONFIGURATION"
        );

      loadSettingsConfig();
    }
  );
});