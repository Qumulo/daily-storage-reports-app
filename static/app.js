function nice_bytes(n){
  var sign = "";
  if(n < 0){
    sign = "-";
    n = Math.abs(n);
  }
  var pres = ["", "K", "M", "G", "T", "P"];
  if(n < 1000){
    return sign + n + " B";
  }
  for(var i = 0; i <= pres.length; i++){
    if(n >= Math.pow(10, i*3) && n < Math.pow(10, i*3+3)){
      return sign + (n / Math.pow(10, i*3)).toFixed(1) + " " + pres[i] + "B";
    }
  }
}

function draw_highlight(name, datas){
    var str = "<dl>" + 
            "<dt>" + name + "</dt>" +
            "<dd class=\"used\">";
    for(var i=0; i<datas.length; i++){
        str += datas[i] + "<br />";
    }
    str += "</dd></dl>";
    return str;
}



function render_capacity(config, args){

    $.getJSON( "get-data-json?d=capacity&path=" + args["path"] + "&start_date=" + args["start_date"] + "&end_date=" + args["end_date"] + "&cluster_name=" + args["cluster_name"], function(json_data) {
        var d = json_data["data"];

        var min_val = d3.min(d, function(v) { return v.total_used_capacity;} );
        var max_val = d3.max(d, function(v) { return v.total_used_capacity;} );
        var first_val = d[0].total_used_capacity;
        var last_val = d[d.length - 1].total_used_capacity;
        var first_date = moment(d[0].timestamp);
        var last_date = moment(d[d.length - 1].timestamp);
        var total_cap = json_data["cluster"]["total_usable_capacity"];
        var top_perc_line = Math.ceil(20 * max_val / total_cap) / 20;
        var bottom_perc_line = Math.floor(20 * max_val / total_cap) / 20;

        if(max_val / total_cap < 0.02){
            top_perc_line = max_val / total_cap;
        }

        config["bindto"] = "#capacity";
        config["data"]["json"] = d;
        config["data"]["keys"]["x"] = "timestamp";
        config["data"]["keys"]["value"] = ["total_used_capacity"];
        config["data"]["names"]["total_used_capacity"] = 'Used Capacity';

        config["axis"]["y"]["max"] = top_perc_line * total_cap;
        config["axis"]["y"]["min"] = min_val * 0.90;
        if(min_val > bottom_perc_line * total_cap)
            config["axis"]["y"]["min"] = bottom_perc_line * total_cap * 0.85;
        config["axis"]["y"]["tick"]["format"] = function (x) { return nice_bytes(x); };
        if(top_perc_line >= 0.05){
            config["grid"]["y"]["lines"].push(
                    { value: top_perc_line * total_cap,
                    text: Math.round(top_perc_line * 100) + "% of Total Capacity",
                    position: 'middle'}
            );
        }
        if(bottom_perc_line > 0){
            config["grid"]["y"]["lines"].push(
                    { value: bottom_perc_line * total_cap,
                    text: Math.round(bottom_perc_line * 100) + "% of Total Capacity",
                    position: 'middle'}
            );
        }
        config["data"]["labels"]["format"]["total_used_capacity"] = function (v, id, i, j) {
                if(i==0 
                || i==(d.length - 1) 
                || (Math.abs(v/first_val-1)>0.01 && Math.abs(v/last_val-1)>0.01 && (v <= min_val*0.99 || v >= max_val * 1.01))
                )
                return nice_bytes(v); 
        };
        config["axis"]["x"]["min"] = first_date.add(-1, "days").format("YYYY-MM-DD");
        config["axis"]["x"]["max"] = last_date.add(1, "days").format("YYYY-MM-DD");
        c3.generate(config);

        var highlight_data = ["<b>" + nice_bytes(last_val) + "</b>"];
        highlight_data[0] += " (" + (100 * last_val / total_cap).toFixed(1) + "%)";
        highlight_data[0] += "<br />of " + nice_bytes( total_cap );
        $("#capacity + .stats").append(draw_highlight("Used Capacity", highlight_data));
        var one_week = null;
        if(d.length >= 7)
            one_week = last_val - d[d.length - 7].total_used_capacity;
        var full_range = (last_val - first_val) / (d.length / 7.0);
        var growth_data = ["Last Week: <b>" + (one_week>0?"+":"") + nice_bytes(one_week) + "</b>"];
        growth_data.push("Last " + Math.ceil(d.length / 7) + " Weeks: <b>" + (full_range>0?"+":"") + nice_bytes(full_range) + "</b>");
        $("#capacity + .stats").append(draw_highlight("Growth Per Week", growth_data));

        var last_date1 = last_date.clone();
        var last_date2 = last_date.clone();
        var d1 = last_date1.add((total_cap - last_val) / one_week, 'week');
        var d2 = last_date2.add((total_cap - last_val) / full_range, 'week');
        var d_avg = (d1 + d2) / 2;
        var last_date1 = moment(d_avg).clone().add(-14, 'day').format("MMM D, YYYY");
        var last_date2 = moment(d_avg).clone().add(14, 'day').format("MMM D, YYYY");


        var fill_data = ["<b>" + last_date1 + " - " + last_date2 + "</b>"];
        $("#capacity + .stats").append(draw_highlight("100% Capacity Forecast", fill_data));
        

        $(".c3-grid").each(function(i, el){
            el.parentNode.insertBefore(el, el.parentNode.firstChild);
        })
    });

}


function render_throughput(config, args){
    $.getJSON( "get-data-json?d=throughput&path=" + args["path"] + "&start_date=" + args["start_date"] + "&end_date=" + args["end_date"]+ "&cluster_name=" + args["cluster_name"], function(json_data) {
        var d = json_data["data"];
        config["bindto"] = "#throughput";
        config["data"]["json"] = d;
        config["data"]["keys"]["x"] = "timestamp";
        config["data"]["keys"]["value"] = ["avg_write_throughput", "avg_read_throughput"];
        config["data"]["names"]["avg_write_throughput"] = 'Write Throughput';
        config["data"]["names"]["avg_read_throughput"] = 'Read Throughput';


        config["data"]["colors"] = {
            avg_write_throughput: '#ff9933',
            avg_read_throughput: '#009999'
          };

        var first_date = moment(d[0].timestamp);
        var last_date = moment(d[d.length - 1].timestamp);
        config["axis"]["x"]["min"] = first_date.add(-1, "days").format("YYYY-MM-DD");
        config["axis"]["x"]["max"] = last_date.add(1, "days").format("YYYY-MM-DD");
        config["axis"]["y"]["tick"]["format"] = function (x) { return nice_bytes(x).replace(".0", "") + "/s"; };
        c3.generate(config);

        var read_avg = d3.mean(d, function(v) { return v.avg_read_throughput;} );
        var write_avg = d3.mean(d, function(v) { return v.avg_write_throughput;} );
        var tput_data = ["Write: <b>" + nice_bytes(write_avg) + "/s</b>"];
        tput_data.push("Read: <b>" + nice_bytes(read_avg) + "/s</b>");
        $("#throughput + .stats").append(draw_highlight("Average Throughput", tput_data));

        var read_max = d3.max(d, function(v) { return v.max_read_throughput;} );
        var write_max = d3.max(d, function(v) { return v.max_write_throughput;} );
        var tput_data = ["Write: <b>" + nice_bytes(write_max) + "/s</b>"];
        tput_data.push("Read: <b>" + nice_bytes(read_max) + "/s</b>");
        $("#throughput + .stats").append(draw_highlight("Max Throughput (1 Hour)", tput_data));

    });
}


function render_iops(config, args){
    $.getJSON( "get-data-json?d=iops&path=" + args["path"] + "&start_date=" + args["start_date"] + "&end_date=" + args["end_date"]+ "&cluster_name=" + args["cluster_name"], function(json_data) {
        var d = json_data["data"];
        config["bindto"] = "#iops";
        config["data"]["json"] = d;
        config["data"]["keys"]["x"] = "timestamp";
        config["data"]["keys"]["value"] = ["avg_iops"];
        config["data"]["names"]["avg_iops"] = 'Average IOPS';
        config["tooltip"]["format"]["value"] = function (value, ratio, id) {
                                                return value.toLocaleString();
                                                };
        var first_date = moment(d[0].timestamp);
        var last_date = moment(d[d.length - 1].timestamp);
        config["axis"]["x"]["min"] = first_date.add(-1, "days").format("YYYY-MM-DD");
        config["axis"]["x"]["max"] = last_date.add(1, "days").format("YYYY-MM-DD");
        c3.generate(config);

        var avg_iops= d3.mean(d, function(v) { return v.avg_iops;} );
        var tput_data = ["IOPS: <b>" + Math.round(avg_iops).toLocaleString() + "</b>"];
        $("#iops + .stats").append(draw_highlight("Average IOPS", tput_data));

    });
}


function render_file_iops(config, args){
    $.getJSON( "get-data-json?d=file_iops&path=" + args["path"] + "&start_date=" + args["start_date"] + "&end_date=" + args["end_date"]+ "&cluster_name=" + args["cluster_name"], function(json_data) {
        var d = json_data["data"];
        config["bindto"] = "#file_iops";
        config["data"]["json"] = d;
        config["data"]["keys"]["x"] = "timestamp";
        config["data"]["keys"]["value"] = ["avg_file_write_iops", "avg_file_read_iops"];
        config["data"]["names"]["avg_file_write_iops"] = 'File Writes';
        config["data"]["names"]["avg_file_read_iops"] = 'File Reads';
        config["data"]["colors"] = {
            avg_file_write_iops: '#ff9933',
            avg_file_read_iops: '#009999'
          };
        config["tooltip"]["format"]["value"] = function (value, ratio, id) {
                                                return value.toLocaleString();
                                                };
        var first_date = moment(d[0].timestamp);
        var last_date = moment(d[d.length - 1].timestamp);
        config["axis"]["x"]["min"] = first_date.add(-1, "days").format("YYYY-MM-DD");
        config["axis"]["x"]["max"] = last_date.add(1, "days").format("YYYY-MM-DD");
        c3.generate(config);

        var read_avg = d3.mean(d, function(v) { return v.avg_file_read_iops;} );
        var write_avg = d3.mean(d, function(v) { return v.avg_file_write_iops;} );
        var tput_data = ["Write: <b>" + Math.round(write_avg).toLocaleString() + "</b>"];
        tput_data.push("Read: <b>" + Math.round(read_avg).toLocaleString() + "</b>");
        $("#file_iops + .stats").append(draw_highlight("Average File IOPS", tput_data));

    });
}


function render_path_stats(){
    $.getJSON( "get-data-json?d=path_stats&path=" + args["path"] + "&start_date=" + args["start_date"] + "&end_date=" + args["end_date"]+ "&cluster_name=" + args["cluster_name"], function(json_data) {
        $("#delta_data_table").css({"width":$("body").width() - 30 + "px !important"});

        var maxes = {};
        var mins = {};
        var new_dd = [];
        var dd = json_data["data"];
        for(var k in dd[0]){
            maxes[k] = 0;
            mins[k] = 0;
        }

        for(var r=0; r < dd.length; r++){
            for(var c in dd[0]){
                if($.isNumeric(dd[r][c])){
                    var n = parseFloat(dd[r][c]);
                    if(Math.abs(n) > maxes[c])
                        maxes[c] = Math.abs(n);
                    if(n < mins[c])
                        mins[c] = n;
                }
            }
        }
        for(var r=0; r < dd.length; r++){
            if(dd[r]["cap"] > maxes["cap"] * 0.02
                || Math.abs(dd[r]["cap_chg"]) > maxes["cap_chg"] * 0.02
                || dd[r]["avg_iops"] > maxes["avg_iops"] * 0.05){
                new_dd.push(dd[r]);
            }   
        }     

        $('#delta_data_table').dataTable( {
            "data": new_dd,
            "autoWidth": false,
            "pageLength": 5000,
            "columns": [
                { "title": "Level", "data":"path_level", "defaultContent":"" },
                { "title": "Path", "data":"path", "defaultContent":"", "className":"path_link" },
                { "title": "Capacity", "data":"cap", "defaultContent":"", "orderSequence": [ "desc", "asc"] },
                { "title": "Capacity Change", "data":"cap_chg", "defaultContent":"", "orderSequence": [ "desc", "asc"] },
                { "title": "IOPS", "data":"avg_iops", "defaultContent":"", "orderSequence": [ "desc", "asc"], "render": function ( data, type, full, meta ) {return (data!=null?data.toLocaleString():"");}}
            ]
        } );


        $('#delta_data_table tr').each(function(){
            $el = $($(this).find("td")[2]);
            if($.isNumeric($el.text())){
                var sz = parseFloat($el.text());
                $el.html("<div class='bb cap' style='width:" + (80*(sz / maxes["cap"])) + "px'></div><div class='cap_num'>" + nice_bytes(sz) + "</div>&nbsp;");
            }else{
                $el.html("<span class='del'>[Deleted]</span>");
            }

            $el = $($(this).find("td")[3]);
            if($.isNumeric($el.text())){
                var sz = parseFloat($el.text());
                var pos_str = "left: 80px";
                var label_style = "text-align: left; left: 80px;";
                if(sz < 0){
                    pos_str = "left: " + (80 - (80*(Math.abs(sz) / maxes["cap_chg"]))) + "px";
                }
                $el.html("<div class='bb cap_chg " + (sz < 0?"neg":"pos")+ "' style='width:" + (80*(Math.abs(sz) / maxes["cap_chg"])) + "px; " + pos_str + "'></div><div class='cap_chg_num' style='" + label_style + "'>" + (sz>0?"+":"") + nice_bytes(sz) + "</div>&nbsp;");
            }

            $el = $($(this).find("td")[4]);
            var iop_val = $el.text().replace(/[,]+/g, "");
            if($.isNumeric(iop_val)){
                var sz = parseFloat(iop_val);
                $el.html("<div class='bb cap' style='width:" + (80*(sz / maxes["avg_iops"])) + "px'></div><div class='cap_num'>" + $el.text() + "</div>&nbsp;");
            }
        });

      $('#delta_data_table tbody tr td:nth-child(3) .cap_num').click(function(){
        path = $(this).parent().parent().children("td:eq(1)").text();
        window.location.href = "/alerts?alert_type=total used capacity&cluster_name=" + cluster_name + "&path=" + path + "&val=" + $(this).text();
      })

      $(".path_link:not(:first)").click(function(){
        $("#path").val($(this).text());
        $("form").submit();
      })


    });    
}



$(document).ready(function(){
    $("#emails").focus(function(){
        $(this).removeClass("unfocus");
        if(/(list of one|email recipients)/.test( $(this).val() )){
            $(this).val("");
        }
    });
    $("#emails").blur(function(){
        if($(this).val() == ""){
            $(this).val("List of one or more email recipients separated by a comma");
            $(this).addClass("unfocus");
        }
    });    
    $("#show_menu_button").click(function(){
        $("#show_menu_button").addClass("hidden").removeClass("visible");
        $("#top_menu").addClass("visible").removeClass("hidden");
    });

    $("#hide_menu_button").click(function(){
        $("#show_menu_button").addClass("visible").removeClass("hidden");
        $("#top_menu").addClass("hidden").removeClass("visible");
    });

    $("select").change(function(){
        window.location.href = "/?cluster_name=" + $(this).val();
    });

  $("#sendit").click(function(){
    $btn = $(this);
    $btn.prop("disabled",true);
    $("#emails").prop("disabled",true);
    var url = "/email?to=" + $("#emails").val() + "&" + $("form").serialize();
    $.get(url, function(){
        $btn.prop("disabled",false);
        $("#emails").prop("disabled",false);
        $("#emails").val("");
    });
  });

  $( "#start_date" ).datepicker({ dateFormat: 'yy-mm-dd' });
  $( "#end_date" ).datepicker({ dateFormat: 'yy-mm-dd' });

  var chart_config = {
    data: {
      xFormat: "%Y-%m-%d",
      colors: {},
      labels: {
        format: {}
      },
      keys: {},
      values: {},
      names: {},
    },
    grid: {
      y: {
        lines: []
      }
    },
    axis: {
      y: {
        tick: {}
      },
      x: {
          type: 'timeseries',
          tick: {
              format: function (x) { return moment(x).format("MMM D"); },
          },
      }
    },
    point: {
      r: 4
    },
    tooltip:{
        format:{}
    }
  };
  args = {"path":base_path, "start_date": start_date, "end_date":end_date, "cluster_name":cluster_name};
  cols = {}
  render_capacity($.extend(true, {}, chart_config), args);
  if(base_path == "/"){
    render_throughput($.extend(true, {}, chart_config), args);
  }
  render_iops($.extend(true, {}, chart_config), args);
  render_file_iops($.extend(true, {}, chart_config), args);
  render_path_stats();

});

