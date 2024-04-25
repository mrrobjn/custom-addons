odoo.define('meeting_room.schedule_view_calendar', function(require) {
    'use strict';
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;

    const config = require('web.config');
    var CalendarController = require("web.CalendarController");
    var CalendarRenderer = require("web.CalendarRenderer");
    var CalendarModel = require("web.CalendarModel");
    var CalendarView = require("web.CalendarView");
    var viewRegistry = require('web.view_registry');

    console.log('querying Calendar');

    var _t = core._t;
    var BookingCalendarController = CalendarController.extend({
        /**
         * @override
         */
        _setEventTitle: function () {
            return _t('Booking Form');
        },
        _onDeleteRecord: function (ev) {
            var self = this;
            var recordID = $(ev.currentTarget).data('id');
            
            var dateStart = ev.data.event.record.id
            console.log(dateStart)
           
            // var dateStart = $('.o_field_widget[name="start_date"]').get().value;
                var dialog = new Dialog(this, {
                title: _t('Delete Confirmation'),
                size: 'medium',
                $content: $(QWeb.render('meeting_room.RecurrentEventUpdate',{
                })),
                buttons: [
                    {
                        text: _t('Delete'),
                        classes: 'btn-danger',
                        close: true,
                        click: function () {
                            var selectedValue = $('input[name="recurrence-update"]:checked').val();
                            
                            // console.log(self.model.data.data[0].id);
                            // debugger
                            console.log(dateStart);
                            rpc.query({
                                model: 'meeting.schedule',
                                method: 'delete_meeting',
                                args: [selectedValue,dateStart],
                            }).then(function (result) {
                                // Handle the delete operation success
                                // For example, refresh the calendar view
                                self.reload();
                            }).catch(function (error) {
                                // Handle the delete operation error
                                console.error('An error occurred while deleting the event:', error);
                            });
                        },
                    },
                    {
                        text: _t('Cancel'),
                        close: true,
                    },
                ],
            });
            dialog.open();
        },
    });
    var BookingPopoverRenderer = CalendarRenderer.extend({
        
    });

    var BookingCalendarRenderer = BookingPopoverRenderer.extend({
    });

    
    var BookingCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: BookingCalendarController,
            Renderer: BookingCalendarRenderer,
            Model: CalendarModel,
        }),
    });
    viewRegistry.add('msm', BookingCalendarView);
});