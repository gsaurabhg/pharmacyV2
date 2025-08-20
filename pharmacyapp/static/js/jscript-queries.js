if(typeof jQuery!=='undefined'){
    console.log('jQuery Loaded');
}
else{
    console.log('not loaded yet');
}


function computeTableColumnTotal(tableId, colNumber)
{
  var result = 0;
  try
  {
    var tableBody = window.document.getElementById(tableId).getElementsByTagName("tbody").item(0);
    var i;
    var howManyRows = tableBody.rows.length;
    for (i=0; i<(howManyRows-1); i++) // skip first and last row (hence i=1, and howManyRows-1)
    {
       var thisTextNode = tableBody.rows[i].cells[colNumber].childNodes.item(0);
       var thisNumber = parseFloat(thisTextNode.data);
       if (!isNaN(thisNumber))
         result += thisNumber;
	 } // end for
  } // end try
  catch (ex)
  {
     window.alert("Exception in function computeTableColumnTotal()\n" + ex);
     result = 0;
  }
  finally
  {
     return result;
  }

}

function finishTable()
{
  var totalPrice1 = computeTableColumnTotal("cartMeds",5);
  var totalPrice = Math.round(totalPrice1*100)/100;
  var totalDiscountedPriceUnrounded = computeTableColumnTotal("cartMeds",7);
  var totalDiscountedPrice = Math.round(totalDiscountedPriceUnrounded*100)/100;
  try
  {
    window.document.getElementById("TP").innerHTML = totalPrice;
    window.document.getElementById("TDP").innerHTML = totalDiscountedPrice;
  }
  catch (ex)
  {
     window.alert("Exception in function finishTable()\n" + ex);
  }
  return;
}

(5,6)
function finishTable_2ClmnSum(colNo1,colNo2)
{
  var totalPrice1 = computeTableColumnTotal("cartMeds",colNo1);
  var totalPrice = Math.round(totalPrice1*100)/100;
  var totalDiscountedPriceUnrounded = computeTableColumnTotal("cartMeds",colNo2);
  var totalDiscountedPrice = Math.round(totalDiscountedPriceUnrounded*100)/100;
  try
  {
    window.document.getElementById("TP").innerHTML = totalPrice;
    window.document.getElementById("TDP").innerHTML = totalDiscountedPrice;
  }
  catch (ex)
  {
     window.alert("Exception in function finishTable()\n" + ex);
  }
  return;
}

function finishTable_retMeds()
{
  var totalReturnAmount = computeTableColumnTotal("cartMeds",9);
  try
  {
    window.document.getElementById("TP").innerHTML = totalReturnAmount;
  }
  catch (ex)
  {
     window.alert("Exception in function finishTable()\n" + ex);
  }
  return;
}


function printDiv(divName) {
     var printContents = document.getElementById(divName).innerHTML;
     var originalContents = document.body.innerHTML;

     document.body.innerHTML = printContents;

     window.print();

     document.body.innerHTML = originalContents;
}


function finishTable_v1(colNo)
{
  var totalPrice = computeTableColumnTotal("daysales",colNo);
  var totalPriceRounded = Math.round(totalPrice*100)/100;
  try
  {
    window.document.getElementById("TPP").innerHTML = totalPriceRounded;
  }
  catch (ex)
  {
     window.alert("Exception in function finishTable()\n" + ex);
  }
  return;
}

function get_batch_no(request_data) {
    // Trim and replace spaces in request_data
    const sanitizedRequestData = request_data.trim().replace(/\s/g, '-_____-');

    // Create the URL to fetch batch numbers
    const url = `/medicineName/${sanitizedRequestData}/get_batch_no`;

    // Send the GET request and handle the response
    $.getJSON(url, function(batchNumbers) {
        // Check if the response contains any batch numbers
        if (batchNumbers.length > 0) {
            // Build the options list using map() for better readability and performance
            const options = ['<option value="">Select Batch No</option>']
			                .concat(batchNumbers.map(batchNo =>
			                    `<option value="${batchNo}">${batchNo}</option>`
			                ))
                .join('');  // Join the array into a single string

            const $batchNoSelect = $("select#batchNo");
            $batchNoSelect.html(options);  // Replace existing options
            // Update the batchNo select dropdown
            $("select#batchNo").attr('disabled', false);
        } else {
            console.error("No batch numbers found in the response");
        }
    }).fail(function() {
        // Handle error if the request fails
        console.error('Failed to fetch batch numbers');
    });
}


function get_quantity(request_data)
{
	var url = "/batchNo/" + request_data + "/get_quantity";
	var batchNo = request_data;
	$.getJSON(url, function(response){
	var quantity = response.quantity;  // Access 'quantity' from the response
	$("#quantity").text("Max Quantity allowed: " + quantity );
	});
}



function printReturnInvoice(divName) {
     var printContents = document.getElementById(divName).innerHTML;
     var originalContents = document.body.innerHTML;

     document.body.innerHTML = printContents;

     window.print();

     document.body.innerHTML = originalContents;
}

function promptForFilename() {
    const filename = prompt("Please enter the filename for the database to be exported:");
    if (filename) {
        document.getElementById("filename").value = filename; // Set the filename in the hidden input
        document.getElementById("dumpForm").submit(); // Submit the form
    }
}

function handleMenuClick(event) {
    event.preventDefault(); // Prevent the default link behavior
    promptForFilename(); // Call the function to show the prompt
}

function handleMenuClick_ld(event) {
    event.preventDefault(); // Prevent the default link behavior
    document.getElementById("loadForm").submit(); // Submit the form
}

function confirmLoadData() {
    return confirm("Are you sure you want to flush old data and load new data from the uploaded JSON file?");
}

function confirmDelete(medName, batchNo, redirectUrl) {
	var confirmMessage = "Are you sure you want to delete " + medName + " with Batch No: "+ batchNo + "?";
	return confirm(confirmMessage);
}

<!-- Add JavaScript to pass active_tab in the URL (if needed) -->
$(document).ready(function() {
    // Set the active tab in the URL to maintain state when clicking tabs
    $('.nav-link').on('click', function (e) {
        var activeTab = $(this).attr('href')?.substring(1);  // Get the category name (e.g., "Urology")
        if (activeTab) {
            window.location.href = "?active_tab=" + activeTab;  // Append the active tab to the URL
        }
    });

    // Make sure the active tab is fetched correctly from the URL
    var activeTab = new URLSearchParams(window.location.search).get('active_tab');

    // Add click event listener for sorting columns, using the activeTab value to build the table ID
    if (activeTab) {
        $('.sort-column').on('click', function () {
            var columnIndex = $(this).index();  // Get the column index (can be adapted to your needs)
            var tableId = "stock-table-" + activeTab.toLowerCase();  // Build the table ID dynamically based on the active tab
            sortTable(columnIndex, tableId);  // Call your sorting function
        });
    }
});


function sortTable(columnIndex, tableId) {
    var table = document.getElementById(tableId);
    if (!table) return; // If table is not found, do nothing
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.rows);
    var dir = table.querySelector('th:nth-child(' + (columnIndex + 1) + ') .sort-icon').innerHTML === '▲' ? 'desc' : 'asc';

    // Update the sort icon
    var headerRow = table.querySelector('thead tr');
    var headerCells = headerRow.querySelectorAll('th');
    headerCells.forEach(function (cell, index) {
        var icon = cell.querySelector('.sort-icon');
        if (index === columnIndex) {
            if (icon) {  // Check if the sort icon exists before modifying it
                icon.innerHTML = dir === 'asc' ? '▲' : '▼'; // Update sort icon
            }
        } else {
            if (icon) {  // Check if the sort icon exists before clearing it
                icon.innerHTML = ''; // Clear other sort icons
            }
        }
    });

    // Perform sorting based on the direction
    rows.sort(function (rowA, rowB) {
        var xValue = rowA.cells[columnIndex].textContent.trim().toLowerCase();
        var yValue = rowB.cells[columnIndex].textContent.trim().toLowerCase();

        // Convert to numbers if possible
        var xNum = parseFloat(xValue);
        var yNum = parseFloat(yValue);

        if (!isNaN(xNum) && !isNaN(yNum)) {
            return (dir === 'asc') ? xNum - yNum : yNum - xNum;
        } else {
            return (dir === 'asc') ? xValue.localeCompare(yValue) : yValue.localeCompare(xValue);
        }
    });

    // Reorder the rows
    rows.forEach(function (row) {
        tbody.appendChild(row); // Reinsert the row back in the table in sorted order
    });
}


//script added to fill the pack size automatically if medicne name and batchNo exist.
// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', function() {
    // Check if the medicineName, batchNo, and other required elements are present in the DOM
    const medicineNameInput = document.getElementById('medicineName');
    const batchNoInput = document.getElementById('batchNo');
    const packInput = document.getElementById('pack');
    const mrpInput = document.getElementById('mrp');
    const expiryDateInput = document.getElementById('expiryDate');

    // Only run the script if the required elements are found
    if (medicineNameInput && batchNoInput && packInput && mrpInput && expiryDateInput) {
        // Add event listeners for input changes on medicineName and batchNo
        medicineNameInput.addEventListener('input', checkMedicineAndBatch);
        batchNoInput.addEventListener('input', checkMedicineAndBatch);
    }

    function checkMedicineAndBatch() {
        var medicineName = medicineNameInput.value;
        var batchNo = batchNoInput.value;

        if (medicineName && batchNo) {
            // Make an AJAX request to get the pack size, MRP, and expiry date based on medicineName and batchNo
            fetch('/get-pack-size/?medicineName=' + encodeURIComponent(medicineName) + '&batchNo=' + encodeURIComponent(batchNo))
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // If a matching record is found, pre-fill the fields if they are not already overridden
                        if (packInput.value === '') {
                            packInput.value = data.pack_size;
                        }

                        if (mrpInput.value === '') {
                            mrpInput.value = data.mrp;
                        }

                        if (expiryDateInput.value === '') {
                            expiryDateInput.value = data.expiry_date;
                        }
                    } else {
                        // If no matching record is found, clear the fields
                        packInput.value = '';
                        mrpInput.value = '';
                        expiryDateInput.value = '';
                    }
                })
                .catch(error => {
                    console.error('Error fetching pack size:', error);
                    // Clear fields on error
                    packInput.value = '';
                    mrpInput.value = '';
                    expiryDateInput.value = '';
                });
        }
    }
});




console.log('End of Java script loading')