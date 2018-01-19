# 头文件
import tensorflow as tf
import numpy as np

# CNN卷积层输入
x = tf.placeholder(tf.float32, [None, 256*42])  # [7080,600]
y_actual = tf.placeholder(tf.float32, shape=[None, 6])  # [7080,7]
inputs = tf.placeholder(tf.int32, shape=())

# 读入真实数据
input_count = 6582
x_s = np.loadtxt('Comnet-14_flow_onehot_without_train.txt')
y_s = np.loadtxt('Comnet-14_flow_onehot_train_label.txt')
train_images = np.array([[0] * 256 for i in range(input_count*42)])
train_labels = np.array([[0] * 6 for i in range(input_count)])
for index in range(input_count*42):
    for j in range(256):
        train_images[index][:] = x_s[index, :]
train_images = tf.reshape(train_images, [-1, 256*42])
for index in range(input_count):
    for k in range(6):
        train_labels[index][:] = y_s[index, :]
dataset = tf.data.Dataset.from_tensor_slices((train_images, train_labels)).shuffle(buffer_size=input_count).batch(1097).repeat()
iterator = dataset.make_initializable_iterator()
one_element = iterator.get_next()

input_count1 = 5580
x_t = np.loadtxt('Comnet-14_flow_onehot_without_test.txt')
y_t = np.loadtxt('Comnet-14_flow_onehot_test_label.txt')
test_images = np.array([[0] * 256 for i in range(input_count1*42)])
test_labels = np.array([[0] * 6 for i in range(input_count1)])
for index in range(input_count1*42):
    for j in range(256):
        test_images[index][:] = x_t[index, :]
test_images = tf.reshape(test_images, [-1, 256*42])
for index in range(input_count1):
    for k in range(6):
        test_labels[index][:] = y_t[index, :]
dataset1 = tf.data.Dataset.from_tensor_slices((test_images, test_labels)).shuffle(buffer_size=input_count1).batch(180).repeat()
iterator1 = dataset1.make_initializable_iterator()
one_element1 = iterator1.get_next()


# LSTM初始化参数
lr = 0.001
training_iters = 3000000
batch_size = 120
n_inputs = 21
n_steps = 64
n_hidden_units = 120
n_classes = 6
keep_prob = 0.5
# RNN_x = tf.placeholder(tf.float32, [None, n_steps, n_inputs])  # [120,64,50]
# RNN_y = tf.placeholder(tf.float32, [None, n_classes])  # [120,7]
weights = {
    'in': tf.Variable(tf.random_normal([n_inputs, n_hidden_units])),  # [50,120]
    'out': tf.Variable(tf.random_normal([n_hidden_units, n_classes]))  # [120,7]
}
biases = {
    'in': tf.Variable(tf.constant(0.1, shape=[n_hidden_units, ])),  # [120,]
    'out': tf.Variable(tf.constant(0.1, shape=[n_classes, ]))  # [7,]
}


# 定义函数，用于初始化权值 W，初始化偏置b，定义卷积层，定义池化层
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)


def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')


def conv2d_6(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 256, 1], padding='SAME')


def max_pool(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 1, 1], padding='SAME')


def max_pool_2(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 1, 1, 1], padding='SAME')


def RNN(X, weights, biases):
    X = tf.reshape(X, [-1, n_inputs])  # [7080*10*5,64] [120*50,64]
    X_in = tf.matmul(X, weights['in']) + biases['in']  # [7080*10*5,120] [120*50,120]
    X_in = tf.reshape(X_in, [-1, n_steps, n_hidden_units])  # [7080,50,120] [120,50,120]

    lstm_cell = tf.contrib.rnn.BasicLSTMCell(n_hidden_units, forget_bias=1.0, state_is_tuple=True)
    lstm_cell = tf.contrib.rnn.DropoutWrapper(cell=lstm_cell, input_keep_prob=1.0, output_keep_prob=keep_prob)
    init_state = lstm_cell.zero_state(inputs, dtype=tf.float32)  # [7080,120] [120,120]

    outputs, final_state = tf.nn.dynamic_rnn(lstm_cell, X_in, initial_state=init_state, time_major=False)  # [7080,50,120],[7080,120]
    results = tf.matmul(final_state[1], weights['out']) + biases['out']
    return results  # [7080,7] [120,7]


# 构建网络
x_image = tf.reshape(x, [-1, 42, 256, 1])  # [7080,10,60]
epsilon = 0.001
mean, var = tf.nn.moments(x_image, axes=[0],)
scale = tf.Variable(tf.ones([1]))
shift = tf.Variable(tf.zeros([1]))
x_image_normal = tf.nn.batch_normalization(x_image, mean, var, shift, scale, epsilon)
# conv1+pool1
W_conv1 = weight_variable([2, 256, 1, 32])
b_conv1 = bias_variable([32])
h_conv1 = tf.nn.relu(conv2d_6(x_image_normal, W_conv1) + b_conv1)  # [7080,10,10,32]
h_pool1 = max_pool(h_conv1)  # [7080,5,10,32]
# BN2
mean_pool1, var_pool1 = tf.nn.moments(h_pool1, axes=[0, 1, 2],)
scale_pool1 = tf.Variable(tf.ones([32]))
shift_pool1 = tf.Variable(tf.zeros([32]))
h_bn_pool1 = tf.nn.batch_normalization(h_pool1, mean_pool1, var_pool1, shift_pool1, scale_pool1, epsilon)
# conv2+pool2
W_conv2 = weight_variable([4, 4, 32, 64])
b_conv2 = bias_variable([64])
h_conv2 = tf.nn.relu(conv2d(h_bn_pool1, W_conv2) + b_conv2)  # [7080,5,10,64]
h_pool2 = max_pool_2(h_conv2)  # [7080,5,10,64]
mean_pool2, var_pool2 = tf.nn.moments(h_pool2, axes=[0, 1, 2],)
scale_pool2 = tf.Variable(tf.ones([64]))
shift_pool2 = tf.Variable(tf.zeros([64]))
h_bn_pool2 = tf.nn.batch_normalization(h_pool2, mean_pool2, var_pool2, shift_pool2, scale_pool2, epsilon)
h_bn_pool2 = tf.reshape(h_bn_pool2, [-1, n_steps*n_inputs])  # [7080,50*64]


lstm_pred = RNN(h_bn_pool2, weights, biases)  # [7080,7]
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=y_actual, logits=lstm_pred))
train_step = tf.train.AdamOptimizer(lr).minimize(cost)
correct_pred = tf.equal(tf.argmax(lstm_pred, 1), tf.argmax(y_actual, 1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


sess = tf.InteractiveSession()
sess.run(tf.global_variables_initializer())
train_images = sess.run(train_images)
test_images = sess.run(test_images)
sess.run(iterator.initializer)
sess.run(iterator1.initializer)

for i in range(100000):
    # train_step.run(feed_dict={x: x_s, y_actual: y_s, keep_prob: 0.5})
    # batch_xs, batch_ys = sess.run(one_element)
    # batch_xs = batch_xs.reshape([batch_size, n_steps, n_inputs])
    batch_xs, batch_ys = sess.run(one_element)
    batch_xs1, batch_ys1 = sess.run(one_element1)
    train_step.run(feed_dict={
        x: train_images,
        y_actual: train_labels,
        inputs: 6582
    })
    if i % 5 == 0:
        train_accuracy = accuracy.eval(feed_dict={
            x: batch_xs,
            y_actual: batch_ys,
            inputs: 1097
        })
        test_accuracy = accuracy.eval(feed_dict={
            x: batch_xs1,
            y_actual: batch_ys1,
            inputs: 180
        })
        # print("CNNstep %d, training accuracy %g" % (i, train_accuracy))
        print("step %d, train accuracy %g" % (i, train_accuracy), ", test accuracy %g" % test_accuracy)

