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
	};
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
