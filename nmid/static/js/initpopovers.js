$(document).ready(function() {

    // Init popovers
    $('[data-toggle="popover"]').popover({
        placement: 'auto',
        html: true
    });

    $(document).on('click', function (e) {
        $('[data-toggle="popover"],[data-original-title]').each(function () {
            // Thanks to Matt Lockyer for this great solution to allow
            // popovers to be closed when the user clicks elsewhere

            //the 'is' for buttons that trigger popups
            //the 'has' for icons within a button that triggers a popup
            if (!$(this).is(e.target) && $(this).has(e.target).length === 0
                && $('.popover').has(e.target).length === 0) {
                (($(this).popover('hide').data('bs.popover') ||
                    {}).inState ||
                    {}).click = false; // fix for BS 3.3.6
            }
        });
    });

    $(document).on('shown.bs.popover', function() {

        // Init dismiss buttons
        $('[data-dismiss="popover"]').click(function() {
            (($(this).parents('.popover').popover('hide').data('bs.popover') ||
                {}).inState ||
                {}).click = false;  // fix for BS 3.3.6
        });
    });
});
