traffic_light = function (subdir, root_element) {
	let me = this;
	this.subdir = subdir;
	this.root_element = root_element;
	this.run=function(interval){
		$.ajax(this.subdir, {
			dataType: "json",
			timeout: interval,
			success: function(data){
					me.got_answer(data);
				   }
		    });
		window.setTimeout(function(){me.run(interval);}, interval );
		};
	this.set_way=function(value){
			$.post(this.subdir, 
				{
					"giveway": value
				},
			);
		},
	this.got_answer=function(data){
		$(".battvoltage", this.root_element).val(data.batt_voltage/100.0);
		if (data.lamp_currents[0]>10) this.red_circle.show(); else this.red_circle.hide();
		if (data.lamp_currents[1]>10) this.yellow_circle.show(); else this.yellow_circle.hide();
		if (data.lamp_currents[2]>10) this.green_circle.show(); else this.green_circle.hide();

	};
	$.ajax("/image/ampel.svg",
		{
		dataType:"text",
		success:function(data){
			$(".tlpicture", this.root_element).replaceWith(data);
			me.red_circle = $(".red", this.root_element);
			me.yellow_circle = $(".yellow", this.root_element);
			me.green_circle = $(".green", this.root_element);
			}
		})
	// Now finally run the stuff
	me.run(250);
	$(".setred",this.root_element).click( function(){
		me.set_way(0);
	});
	$(".setgreen",this.root_element).click( function(){
		me.set_way(1);
	});
}

$("document").ready(function()
{
    new traffic_light("/interface/status", $("#light1"));

});
