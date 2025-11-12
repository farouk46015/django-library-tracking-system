import logging
from celery import shared_task , group
from .models import Loan
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass



@shared_task(bind=True)
def send_overdue_loan_notification(loan_id):
    """ Send email for the members which has overdue loans """
    try:
        loan = Loan.objects.select_related('member__user' , 'book').get(id=loan_id) 
        user = loan.member.user
        user_email = user.email
        book_title = loan.book.title
        

        if not user_email:
            logger.warning(f"user {user.username} does not have email")
            raise ValueError(f"user {user.username} does not have email")
        
        send_mail(
            subject='Book Loan Overdue',
            message=f'Hello {user.username},\n\nYou have overdue loan on book "{book_title}".\nPlease should returned it in {loan.return_date}',
            rom_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
    
    except Loan.DoesNotExist:
        logger.error(f"laon {loan_id} does not exit")

    except Exception as e:
        logger.error(f"Error in task loan notifiction {e}")
        



@shared_task
def check_overdue_laons() -> str:
    """ Task for checking the over due loans run daily base """
    today = timezone.now().date()

    overdue_laons_ids = list(
        Loan.objects.filter(
            is_returned=False,
            return_date_lt=today
        ).values_list('id' ,flat=True)
    )

    overdue_laons_ids_cournt = len(overdue_laons_ids)
    logger.info(f"we have {overdue_laons_ids_cournt} overdue loans")

    if overdue_laons_ids_cournt > 0 :
        job = group(
            send_overdue_loan_notification.s(loan_id) for loan_id in overdue_laons_ids
        )

        job.apply_async()

    logger.info('No active overdue loans')
    return f"No active overdue loans"

    
