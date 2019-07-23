function isVisible(elem, partialOk) {
  /* Check if element is in the viewport. Taken from:
    * <https://stackoverflow.com/a/488073/1291812> */
  var docViewTop = $(window).scrollTop();
  var docViewBottom = docViewTop + $(window).height();

  var elemTop = $(elem).offset().top;
  var elemBottom = elemTop + $(elem).height();

  if (!partialOk) {
    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
  } else {
    var aboveViewport = ((elemTop <= docViewTop) &&
                         (elemBottom <= docViewTop));
    var belowViewport = ((elemTop >= docViewBottom) &&
                         (elemBottom >= docViewBottom));
    return !aboveViewport && !belowViewport;
  }
}

function updateContainer(container) {
  $('.active').removeClass('active');
  $(container).addClass('active');
  $(container).find('.labels').focus();
}

$(function() {
  // var topSpace = 5;
  $('#preview').hide();

  // HACK: Add new line before last two labels:
  $('.labels').each(
    (_, y) => $(y).find('input[type="checkbox"]').eq(4).before('<br/>'))
  $('.labels').each(
    (_, y) => $(y).find('input[type="checkbox"]').eq(6).before('<br/>'))
  updateContainer($('.image-label-container').eq(0));

  $('.labels').focus(function() {
    if (!$(this).parent().hasClass('active')) {
      updateContainer($(this).parent());
    }
  });

  $(window).keypress(function(event) {
    if ($('input:text').is(':focus')) {
      return;
    }
    if (event.key == 'j' || event.key == 'k') {
      var topOffsets = $('.image-label-container').map(function() {
        return {
          'object': $(this),
          'offset': $(this).offset().top - $(window).scrollTop()
        };
      });

      var spacer = 10;
      var toSelect;
      if (event.key == 'j') {
        toSelect = $('.active').next('.image-label-container');
        if (toSelect.length == 0) {
          return;
        }
      } else {
        toSelect = $('.active').prev('.image-label-container')
        if (toSelect.length == 0) {
          return;
        }
      }
      var elementOffset = $(toSelect).offset();
      var elementMid = toSelect.offset().top + toSelect.height() / 2;
      $([document.documentElement, document.body]).animate({
        scrollTop: Math.max(0,
          elementMid - ($(window).height() / 2))
      }, 100);
      updateContainer(toSelect);
      // toSelect.scrollIntoView({'behavior': 'instant'});
    } else if (!isNaN(event.key)) {
      var label_index = parseInt(event.key);
      if (label_index == 0) {
        label_index = 9;
      } else {
        label_index -= 1;
      }
      var labels = $('.active').find('input');
      if (label_index < 0 || label_index >= labels.length) {
        return;
      }
      var label_object = labels.eq(label_index);
      label_object.prop('checked', !label_object.prop('checked'));
    } else if (event.key == 'm') {
      // Hack: hit `q` and `a` when `m` is hit.
      var labelObjects = $('.active').find('input.keyboard-q');
      labelObjects.prop('checked', !labelObjects.prop('checked'));
      var labelObjects = $('.active').find('input.keyboard-a');
      labelObjects.prop('checked', !labelObjects.prop('checked'));
    } else if (event.key == 'n') {
      $('.active').find('input').prop('checked', false);
    } else if (event.key == 'l') {
      // toggle label visibility
      $('.name').toggleClass('hidden-transparent');
    } else {
      var labelObjects = $('.active').find('input.keyboard-' + event.key);
      labelObjects.prop('checked', !labelObjects.prop('checked'));
    }
  });

  $('form').submit(function() {
    var error = false;
    var numUnlabeled = 0;
    $('.labels').each(function(i, labels) {
      if ($(labels).find('input:checked').length == 0) {
        numUnlabeled++;
        $(labels).parent().addClass('container-error');
      } else {
        $(labels).parent().removeClass('container-error');
      }
    });
    if (numUnlabeled > 0) {
      if (numUnlabeled == 1) {
        $('#error').html('One image is unlabeled, please fix.');
      } else {
        $('#error').html(numUnlabeled + ' images unlabeled, please fix.');
      }
      $('#error').show()
      return false;
    } else {
      $('#error').hide();
      return true;
    }
  });

  var addedHandler = false;
  $('.to-label-container img').click(function() {
    var preview = $('#preview');
    if (!addedHandler) {
      preview.click(function() {$(this).hide()});
      addedHandler = true;
    }
    if (preview.length == 0) {
      $('body').append("<img id='preview'></img>");
      preview = $('#preview');
      preview.click(function() {$(this).hide()});
      addedHandler = true;
    }
    var currentSrc = $(this).attr('src');
    if (preview.is(':visible') && preview.attr('src') == currentSrc) {
      preview.hide();
    } else {
      preview.attr('src', currentSrc).show();
      preview.css({'width': '90%', 'height': 'auto', 'left': '5%'});
      if (preview.height() > 0.9 * $(window).height()) {
        preview.css({'width': 'auto', 'height': '90%'});
        var space = ($(window).width() - preview.width()) / 2;
        console.log($(window).width());
        console.log(preview.width());
        preview.css({'left': space.toString() + 'px'});
        console.log({'left': space.toString() + 'px'});
      } else {
        var space = ($(window).height() - preview.height()) / 2;
        preview.css({'top': space.toString() + 'px'});
        console.log({'top': space.toString() + 'px'});
      }
    }
  });

  $('#preview').click(() => $(this).hide());
});
