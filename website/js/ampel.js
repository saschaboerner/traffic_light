traffic_light = function (subdir, root_element) {
	let me = this;
	this.error_count = 0;
	this.subdir = subdir;
	this.root_element = root_element;
	this.group_key = "";
	this.run=function(interval){
		$.ajax(me.subdir, {
			dataType: "json",
			timeout: interval,
			success: function(data){
					me.got_answer(data);
				   },
			error: function(jqXHR, textStatus, errorThrown){
				me.error(textStatus);	
			}
		    });
		window.setTimeout(function(){me.run(interval);}, interval );
		};
	this.set_way=function(value){
			$.post(me.subdir,
				{
					"giveway": value,
					"key": me.group_key
				},
			);
		};
	this.error=function(textStatus){
		me.error_count++;
		if (me.error_count>4){
			me.red_circle.hide();
			me.yellow_circle.hide();
			me.green_circle.hide();
		}
	};
	this.got_answer=function(data){
		me.error_count = 0;
		$(".battvoltage", me.root_element).val(data.batt_voltage/100.0);
		if (data.lamp_currents[0]>10) me.red_circle.show(); else me.red_circle.hide();
		if (data.lamp_currents[1]>10) me.yellow_circle.show(); else me.yellow_circle.hide();
		if (data.lamp_currents[2]>10) me.green_circle.show(); else me.green_circle.hide();

	};
	$.ajax("/image/ampel.svg",
		{
		dataType:"text",
		success:function(data){
			$(".tlpicture", me.root_element).replaceWith(data);
			me.red_circle = $(".red", me.root_element);
			me.yellow_circle = $(".yellow", me.root_element);
			me.green_circle = $(".green", me.root_element);
			me.error_count = 0;
            // Now finally run the stuff after loading
            me.run(250);
			},
		
		});
	$(".setred",this.root_element).click( function(){
		me.set_way(0);
	});
	$(".setgreen",this.root_element).click( function(){
		me.set_way(1);
	});
	let groupkey = $(".groupkey",this.root_element);
	groupkey.change(function(data){
		me.group_key = groupkey.val();
	});
}

traffic_lights=[];
$("document").ready(function()
{
	$.ajax("/interface",
		{
		dataType:"json",
		success:function(data){
            let original = $(".traffic_light_area");
            let skel = original.clone();
            original.detach();
            let section = $("#uebersicht");//skel.parent();
            for (var x in data){
                let name = data[x];
                let local_copy = skel.clone();
                local_copy.attr("id", name);
                new traffic_light("/interface/"+name, local_copy);
                section.append(local_copy);
            }
		},
	});
});

function hex(x) { return (x.map(function (x) {return x.toString(16);})).join("") }

transportWrapper={
		key:'',
		encapsulate: function(challenge, message){
			message['_time'] = new Date();
			message['challenge'] = challenge;
			let hmac = new sha256.HMAC(transportWrapper.key);
			let raw = JSON.stringify(message);
			hmac.update(raw);
			let result = { hash:hex(hmac.digest()),
						   raw:raw};
			return result;
		},
		decapsulate: function(message){
			let hmac = new sha256.HMAC(transportWrapper.key);
			hmac.update(message.raw);
			if ( hex(hmac.digest()) === message.hash ){
					return JSON.parse(message.raw);
			} else {
					return null;
			}
		},
};
