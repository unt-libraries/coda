$.fn.equalHeight = function() {
    var maxHeight = 0;
    return this.each(function(index, box) {
        var boxHeight = $(box).height();
        maxHeight = Math.max(maxHeight, boxHeight);
    }).height(maxHeight);
};

$(document).ready(function() {
    $('.dashboard-row .dashboard-box').equalHeight();
	
});
$(window).resize(function(){
    $('.dashboard-row .dashboard-box').css('height','auto');
    $('.dashboard-row .dashboard-box').equalHeight();
});