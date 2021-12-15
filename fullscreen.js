var oldHeight;

function openFullscreen(elemId) {
  var elem = document.getElementById(elemId);

  oldHeight = document.getElementById("mynetwork").style.height;
  document.getElementById('mynetwork').style.height = "100%";

  if (elem.requestFullscreen) {
    elem.requestFullscreen();
  } else if (elem.webkitRequestFullscreen) {
    elem.webkitRequestFullscreen();
  } else if (elem.msRequestFullscreen) {
    elem.msRequestFullscreen();
  }
}

document.addEventListener('fullscreenchange', (event) => {
    if (!document.fullscreenElement) {
        document.getElementById("mynetwork").style.height = oldHeight;
    }
});