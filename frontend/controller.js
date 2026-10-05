$(document).ready(function () {
  // Display Speak Message
  eel.expose(DisplayMessage);
  function DisplayMessage(message) {
    if (!message) return;
    try {
      $(".siri-message li:first").text(message);
      $(".siri-message").textillate("start");
      $("#WishMessage").text(message);
    } catch (e) {
      console.log("DisplayMessage error: ", e);
    }
  }

  eel.expose(ShowHood);
  function ShowHood() {
    var activePanel = $(".jarvis-panel.active").attr("id");
    if (activePanel === "panel-home" || !activePanel) {
      $("#Oval").attr("hidden", false).show();
    }
    $("#SiriWave").attr("hidden", true).hide();
  }

  eel.expose(senderText);
  function senderText(message) {
    var chatBox = document.getElementById("chat-canvas-body");
    if (chatBox && message && message.trim() !== "") {
      chatBox.innerHTML += `<div class="row justify-content-end mb-3">
          <div class="width-size">
            <div class="sender_message">
              <div class="small fw-bold text-light opacity-75 mb-1"><i class="bi bi-person-fill"></i> YOU</div>
              ${message}
            </div>
          </div>
      </div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }

  eel.expose(receiverText);
  function receiverText(message) {
    var chatBox = document.getElementById("chat-canvas-body");
    if (chatBox && message && message.trim() !== "") {
      chatBox.innerHTML += `<div class="row justify-content-start mb-3">
          <div class="width-size">
            <div class="receiver_message">
              <div class="small fw-bold text-cyan opacity-75 mb-1"><i class="bi bi-robot"></i> JARVIS</div>
              ${message}
            </div>
          </div>
      </div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }

  eel.expose(hideLoader);
  function hideLoader() {
    $("#Loader").attr("hidden", true).hide();
    $("#FaceAuth").attr("hidden", false).show();
  }

  // Hide Face auth and display Face Auth success animation
  eel.expose(hideFaceAuth);
  function hideFaceAuth() {
    $("#FaceAuth").attr("hidden", true).hide();
    $("#FaceAuthSuccess").attr("hidden", false).show();
  }

  // Hide success and display hello greet
  eel.expose(hideFaceAuthSuccess);
  function hideFaceAuthSuccess() {
    $("#FaceAuthSuccess").attr("hidden", true).hide();
    $("#HelloGreet").attr("hidden", false).show();
  }

  // Hide Start Page and display main core
  eel.expose(hideStart);
  function hideStart() {
    $("#Start").fadeOut(500, function () {
      $(this).attr("hidden", true).css("display", "none");
    });
    $("#JarvisHeader").css("opacity", "1");

    setTimeout(function () {
      $("#Oval").addClass("animate__animated animate__zoomIn");
      $("#Oval").attr("hidden", false).show();
    }, 600);
  }

  // Manual bypass authentication
  eel.expose(bypassAuth);
  function bypassAuth() {
    hideStart();
  }

  // Wire bypass button: immediately transition DOM then notify backend
  $(document).on("click", "#bypassAuthBtn", function (e) {
    if (e) e.preventDefault();
    hideStart();
    if (window.eel && eel.bypassAuth) {
      try {
        eel.bypassAuth()();
      } catch (err) {
        console.log("bypassAuth error: ", err);
      }
    }
  });
});