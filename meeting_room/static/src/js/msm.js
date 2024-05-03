odoo.define("meeting_room.schedule_view_calendar", function (require) {
  "use strict";
  var core = require("web.core");
  var Dialog = require("web.Dialog");
  var rpc = require("web.rpc");
  var QWeb = core.qweb;

  const config = require("web.config");
  var CalendarController = require("web.CalendarController");
  var CalendarRenderer = require("web.CalendarRenderer");
  var CalendarModel = require("web.CalendarModel");
  var CalendarView = require("web.CalendarView");
  var viewRegistry = require("web.view_registry");
  var session = require("web.session");
  // user = session.uid

  var _t = core._t;
  var BookingCalendarController = CalendarController.extend({
    /**
     * @override
     */
    _setEventTitle: function () {
      return _t("Booking Form");
    },
    _onDeleteRecord: function (ev) {
      var self = this;
      var recordID = $(ev.currentTarget).data("id");

      var dateStart = ev.data.event.record.id;
      console.log(ev);

      // var dateStart = $('.o_field_widget[name="start_date"]').get().value;
      var dialog = new Dialog(this, {
        title: _t("Delete Confirmation"),
        size: "medium",
        $content: $(QWeb.render("meeting_room.RecurrentEventUpdate", {})),
        buttons: [
          {
            text: _t("Delete"),
            classes: "btn-danger",
            close: true,
            click: function () {
              var selectedValue = $(
                'input[name="recurrence-update"]:checked'
              ).val();

              rpc
                .query({
                  model: "meeting.schedule",
                  method: "delete_meeting",
                  args: [selectedValue, dateStart],
                })
                .then(function (result) {
                  self.reload();
                })
                .catch(function (error) {
                  Dialog.alert(this, error.message.data.message);
                });
            },
          },
          {
            text: _t("Cancel"),
            close: true,
          },
        ],
      });
      dialog.open();
      dialog.o;
    },
  });
  var BookingPopoverRenderer = CalendarRenderer.extend({});

  var BookingCalendarRenderer = BookingPopoverRenderer.extend({
    /**
     * @override
     */
    _renderEventPopover: function (eventData, $eventElement) {
      var self = this;
      console.log(
        eventData._def.extendedProps.record.user_id[0],
        session.user_id[0]
      );
      // Initialize popover widget
      var calendarPopover = new self.config.CalendarPopover(
        self,
        self._getPopoverContext(eventData)
      );

      if (
        eventData._def.extendedProps.record.user_id[0] !== session.user_id[0]
      ) {
        calendarPopover._canDelete = false;
      }
      // console.log(calendarPopover);

      calendarPopover.appendTo($("<div>")).then(() => {
        $eventElement
          .popover(self._getPopoverParams(eventData))
          .on("shown.bs.popover", function () {
            self._onPopoverShown($(this), calendarPopover);
          })
          .popover("show");
      });
    },
  });

  var BookingCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
      Controller: BookingCalendarController,
      Renderer: BookingCalendarRenderer,
      Model: CalendarModel,
    }),
  });
  viewRegistry.add("msm", BookingCalendarView);
});