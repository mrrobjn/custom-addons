odoo.define("booking_room.schedule_view_calendar", function (require) {
  "use strict";
  var core = require("web.core");
  var Dialog = require("web.Dialog");
  var dialogs = require("web.view_dialogs");
  var rpc = require("web.rpc");
  var QWeb = core.qweb;

  const config = require("web.config");
  var CalendarController = require("web.CalendarController");
  var CalendarRenderer = require("web.CalendarRenderer");
  var CalendarModel = require("web.CalendarModel");
  var CalendarView = require("web.CalendarView");
  var viewRegistry = require("web.view_registry");
  var session = require("web.session");
  function dateToServer(date) {
    return date.clone().utc().locale("en").format("YYYY-MM-DD HH:mm:ss");
  }
  function default_start_minutes() {
    let current_time = new Date();
    let current_hour = current_time.getUTCHours();
    let current_minute = Math.ceil(current_time.getMinutes() / 15 + 1) * 15;

    return { current_hour, current_minute };
  }
  function default_end_minutes() {
    let current_time = new Date();
    let current_hour = current_time.getUTCHours();
    let current_minute =
      Math.ceil(current_time.getMinutes() / 15 + 1) * 15 + 30;

    return { current_hour, current_minute };
  }
  var _t = core._t;
  var BookingCalendarController = CalendarController.extend({
    /**
     * @override
     */
    _onOpenCreate: function (event) {
      var self = this;
      const mode = this.mode;
      if (["year", "month"].includes(this.model.get().scale)) {
        event.data.allDay = true;
      }
      var data = this.model.calendarEventToRecord(event.data);
      var context = _.extend(
        {},
        this.context,
        event.options && event.options.context
      );
      if (data.name) {
        context.default_name = data.name;
      }
      if (mode === "month" || mode === "year") {
        let current_time = new Date();

        let startTime = default_start_minutes();
        var newStartDate = moment(data[this.mapping.date_start])
          .hour(startTime.current_hour)
          .minute(startTime.current_minute);
        if (current_time.getDay > 7) {
          newStartDate = newStartDate.subtract(1, "day");
        }
        var formattedStartDate = newStartDate.format("YYYY-MM-DD HH:mm:ss");
        context["default_" + this.mapping.date_start] =
          formattedStartDate || null;

        let endTime = default_end_minutes();
        var newEndDate = moment(data[this.mapping.date_stop])
          .hour(endTime.current_hour)
          .minute(endTime.current_minute);
        if (current_time.getDay > 7) {
          newEndDate = newEndDate.subtract(1, "day");
        }
        var formattedDateStop = newEndDate.format("YYYY-MM-DD HH:mm:ss");
        context["default_" + this.mapping.date_stop] = formattedDateStop;
      } else {
        context["default_" + this.mapping.date_start] =
          data[this.mapping.date_start] || null;
        if (this.mapping.date_stop) {
          context["default_" + this.mapping.date_stop] =
            data[this.mapping.date_stop] || null;
        }
      }
      if (this.mapping.date_delay) {
        context["default_" + this.mapping.date_delay] =
          data[this.mapping.date_delay] || null;
      }
      if (this.mapping.all_day) {
        context["default_" + this.mapping.all_day] =
          data[this.mapping.all_day] || null;
      }
      for (var k in context) {
        if (context[k] && context[k]._isAMomentObject) {
          context[k] = dateToServer(context[k]);
        }
      }
      var options = _.extend({}, this.options, event.options, {
        context: context,
        title: this._setEventTitle(),
      });
      if (this.quick != null) {
        this.quick.destroy();
        this.quick = null;
      }
      if (
        !options.disableQuickCreate &&
        !event.data.disableQuickCreate &&
        this.quickAddPop
      ) {
        this.quick = new QuickCreate(this, true, options, data, event.data);
        this.quick.open();
        this.quick.opened(function () {
          self.quick.focus();
        });
        return;
      }
      if (this.eventOpenPopup) {
        if (this.previousOpen) {
          this.previousOpen.close();
        }
        this.previousOpen = new dialogs.FormViewDialog(self, {
          res_model: this.modelName,
          context: context,
          title: options.title,
          view_id: this.formViewId || false,
          disable_multiple_selection: true,
          on_saved: function () {
            if (event.data.on_save) {
              event.data.on_save();
            }
            self.reload();
          },
        });
        this.previousOpen.on("closed", this, () => {
          if (event.data.on_close) {
            event.data.on_close();
          }
        });
        this.previousOpen.open();
      } else {
        this.do_action({
          type: "ir.actions.act_window",
          res_model: this.modelName,
          views: [[this.formViewId || false, "form"]],
          target: "current",
          context: context,
        });
      }
    },
    _onOpenEvent: function (event) {
      var self = this;
      var id = event.data._id;
      id = id && parseInt(id).toString() === id ? parseInt(id) : id;
      if (!this.eventOpenPopup) {
        this._rpc({
          model: self.modelName,
          method: "get_formview_id",
          //The event can be called by a view that can have another context than the default one.
          args: [[id]],
          context: event.context || self.context,
        }).then(function (viewId) {
          self.do_action({
            type: "ir.actions.act_window",
            res_id: id,
            res_model: self.modelName,
            views: [[viewId || false, "form"]],
            target: "current",
            context: event.context || self.context,
          });
        });
        return;
      }

      var options = {
        res_model: self.modelName,
        res_id: id || null,
        context: event.context || self.context,
        title: event.data.title
          ? _.str.sprintf(_t("Open: %s"), event.data.title)
          : "Booking Detail",
        on_saved: function () {
          if (event.data.on_save) {
            event.data.on_save();
          }
          self.reload();
        },
      };
      if (this.formViewId) {
        options.view_id = parseInt(this.formViewId);
      }
      new dialogs.FormViewDialog(this, options).open();
    },
    _setEventTitle: function () {
      return _t("Booking Form");
    },
    _onDeleteRecord: function (ev) {
      var self = this;

      var id = ev.data.event.record.id;

      var dialog = new Dialog(this, {
        title: _t("Delete Confirmation"),
        size: "medium",
        $content: $(QWeb.render("booking_room.RecurrentEventUpdate", {})),
        buttons: [
          {
            text: _t("OK"),
            classes: "btn btn-primary",
            close: true,
            click: function () {
              var selectedValue = $(
                'input[name="recurrence-update"]:checked'
              ).val();

              rpc
                .query({
                  model: "meeting.schedule",
                  method: "delete_meeting",
                  args: [selectedValue, id],
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

      let calendarPopover = new self.config.CalendarPopover(
        self,
        self._getPopoverContext(eventData)
      );

      rpc
        .query({
          model: "meeting.schedule",
          method: "check_hr",
          args: [],
        })
        .then(function (result) {
          const record = eventData._def.extendedProps.record;
          const date = new Date();
          if (
            result === false &&
            (record.user_id[0] !== session.uid || record.start_date._d < date)
          ) {
            calendarPopover._canDelete = false;
            calendarPopover.isEventEditable = function () {
              return false;
            };
          }
        })
        .catch(function (error) {
          console.log(error);
        })
        .finally(function () {
          calendarPopover.appendTo($("<div>")).then(() => {
            $eventElement
              .popover(self._getPopoverParams(eventData))
              .on("shown.bs.popover", function () {
                self._onPopoverShown($(this), calendarPopover);
              })
              .popover("show");
          });
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
