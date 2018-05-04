/**
	Purpose of this file is to bind events from elements of the DOM to specific functions
**/

var Events = class events{
	constructor(baseURI){
		this.baseURI = baseURI;
  	}

  	yourWaterQuality(){
  		//$("#submit-item-code").on("click", addItemCode);
		$("#product-code").on("click", addItemCode);
  		$("#add-address").on("click", addAddress);

  		function addAddress(){
  			let address = $("#address").val();
  			let getUrl = window.location;
			let baseUrl = getUrl .protocol + "//" + getUrl.host + "/" + getUrl.pathname.split('/')[0];
  			let uri = baseUrl + "addAddress";
  			let urlObj = new URL(getUrl);
  			let itemCode = urlObj.searchParams.get("item-code");

  			var request = $.ajax({
		        url: uri,
		        type: "post",
		        data: {item_code: itemCode, address: address}
		    });

		    // Callback handler that will be called on success
		    request.done(function (response, textStatus, jqXHR){
		        // Log a message to the console
		        console.log("Hooray, it worked! and here is the response: \t" + response);
		    });
			
  		}

  		function addItemCode(){
  			let code = $("#item-code").val();
  			window.location.replace(window.location.href + "?item-code=" + code);
  		}

  	}
}