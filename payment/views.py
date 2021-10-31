from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order
import braintree
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from io import BytesIO
import weasyprint
# Create your views here.

gateway = braintree.BraintreeGateway(settings.BRAINTREE_CONF)

def payment_process(request):
	order_id = request.session.get('order_id')
	order = get_object_or_404(Order,
							  id=order_id)
	total_cost = order.get_total_cost()
	if request.method == 'POST':
		# Получение токена для транзакций.
		nonce = request.POST.get('payment_method_nonce', None)
		# Создание и сохраненеи транзакций.
		result = gateway.transaction.sale({
			'amount': f'{total_cost:.2f}',
			'payment_method_nonce': nonce,
			'options': {
				'submit_for_settlement': True
			}
		})
		if result.is_success:
			# Отметка заказа как оплаченного.
			order.paid = True
			# Сохранение ID транзакий в заказа.
			order.braintree_id = result.transaction.id
			order.save()

			# Создание электронного сообщения.
			subject = 'My Shop - Invoice no. {}'.format(order.id)
			message = 'Please, find attached the invoice for your purchase.'
			email = EmailMessage(subject, message,
								 "kajnazarov06@mail.ru",
								 [order.email])
			# Формирование PDF.
			html = render_to_string('orders/order/pdf.html',
									{'order': order})
			out = BytesIO()
			stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')]
			weasyprint.HTML(string=html)\
					  .write_pdf(out, stylesheets=stylesheets)
			# Прикрепляем PDF к электронному сообщению.
			email.attach('order_{}.pdf'.format(order.id),
						 out.getvalue(),
						 'appliсation/pdf')
			# Отправка сообщения.
			email.send()
			
			return redirect('payment:done')
		else:
			return redirect('payment:canceled')
	else:
		# Формирование одноразового токена для JavaScript SDK.
		client_token = gateway.client_token\
					   .generate(params={'merchant_account_id': 
					   					 settings.BRAINTREE_MERCHANT_ID})
		
		return render(request,
				  	'payment/process.html',
				  	{'order': order,
				  	 'client_token': client_token
				   	})

def payment_done(request):
	return render(request,
				  'payment/done.html')

def payment_canceled(request):
	return render(request,
				  'payment/canceled.html')