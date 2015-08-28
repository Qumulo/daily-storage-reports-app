var system = require('system');
var args = system.args;
var fs = require('fs')

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

var config = JSON.parse(fs.read('config.json'));
console.log("Rendering: " + config["url"] + '/?phantom=yes&' + args[1]);
page.open(config["url"] + '/?phantom=yes&' + args[1], function(status) {
  console.log("Status: " + status);
  if(status === "success") {
    setTimeout(function() {
        page.render(args[2]);
        phantom.exit();
    }, 2000);
  }
});