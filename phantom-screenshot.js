var system = require('system');
var args = system.args;

var page = require('webpage').create();
page.paperSize = {
  width: '8.5in',
  height: '11in',
  margin: {
    top: '30px',
  }  
}

page.viewportSize = {
  width: 1280,
  height: 900
};

page.open('http://localhost:8080/?phantom=yes&' + args[1], function(status) {
  console.log("Status: " + status);
  if(status === "success") {
    setTimeout(function() {
        page.render(args[2]);
        phantom.exit();
    }, 2000);
  }
});
