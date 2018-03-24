/* Set the width of the side navigation to 250px and the left margin of the page content to 250px */
function openNav() {
    document.getElementById("mySidenav").style.width = "250px";
    document.getElementById("main").style.marginLeft = "250px";
}

/* Set the width of the side navigation to 0 and the left margin of the page content to 0 */
function closeNav() {
    document.getElementById("mySidenav").style.width = "0";
    document.getElementById("main").style.marginLeft = "0";
}


/* Google Maps */
var map;
function initMap() {

	var myLatLng = new google.maps.LatLng(42.349341, -71.103982);
	var mapOptions = {
		zoom: 15,
		center: myLatLng
	}
	var map = new google.maps.Map(document.getElementById('map'), mapOptions);

	var marker = new google.maps.Marker({
		position: myLatLng,
		map: map,
		title: 'Marker'
	})
}